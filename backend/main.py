"""
AstroGen — FastAPI Backend
Runs on http://localhost:8001
All model inference, DB operations, and Gemini calls go through here.
Frontend (PyQt6) calls these endpoints via requests library.
"""

import os
import sys
import base64
import io
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from database import (
    create_session, get_all_sessions, rename_session, delete_session,
    add_message, get_session_messages, get_session_context,
    save_generated_image, get_all_generated_images, image_to_base64,
    save_user_profile
)
from models import (
    generate_image_lora, generate_image_gan, caption_image,
    get_model_status, enrich_prompt
)
from gemini import ask_gemini, is_gemini_available

app = FastAPI(title="AstroGen API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.staticfiles import StaticFiles
import threading

# Mount the static directory for generated images
app.mount("/generated", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "data", "generated")), name="generated")

@app.on_event("startup")
def preload_models():
    print("[Models] Preloading pipelines in background thread...")
    try:
        from models import _load_lora_pipeline
        threading.Thread(target=lambda: _load_lora_pipeline() if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'models', 'lora', 'astrogen_lora.safetensors')) else None, daemon=True).start()
    except Exception as e:
        print(f"[Models] Preload error: {e}")

# ── Pydantic Models ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "lora_sd"          # "lora_sd" | "vae_gan"
    session_id: Optional[int] = None
    num_steps: int = 30
    guidance_scale: float = 7.5
    seed: Optional[int] = None
    width: int = 512
    height: int = 512

class ChatRequest(BaseModel):
    message: str
    session_id: int
    image_b64: Optional[str] = None  # base64 image for multimodal

class SessionRenameRequest(BaseModel):
    title: str

class CaptionRequest(BaseModel):
    image_b64: str
    question: Optional[str] = None
    session_id: Optional[int] = None


# ── Health / Status ─────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "AstroGen API running", "version": "1.0.0"}


@app.get("/status")
def status():
    """Returns model availability and system info."""
    model_status = get_model_status()
    return {
        "models": model_status,
        "gemini": is_gemini_available(),
        "db_sessions": len(get_all_sessions()),
    }


# ── Sessions ────────────────────────────────────────────────────────────────

@app.get("/sessions")
def list_sessions():
    return get_all_sessions()


@app.post("/sessions")
def new_session(title: str = "New Chat"):
    session_id = create_session(title)
    return {"session_id": session_id, "title": title}


@app.put("/sessions/{session_id}")
def update_session(session_id: int, body: SessionRenameRequest):
    rename_session(session_id, body.title)
    return {"ok": True}


@app.delete("/sessions/{session_id}")
def remove_session(session_id: int):
    delete_session(session_id)
    return {"ok": True}


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: int):
    return get_session_messages(session_id)


# ── Image Generation ─────────────────────────────────────────────────────────

@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Generate astronomical image.
    Model choices:
      lora_sd  — LoRA fine-tuned Stable Diffusion (text-to-image)
      vae_gan  — VAE-GAN decoder (random generation)
    """
    # Save user message to chat history immediately before slow generation
    if req.session_id and req.prompt:
        try:
            add_message(
                session_id=req.session_id,
                role='user',
                content=req.prompt,
                msg_type='text'
            )
        except Exception as e:
            print(f"[Backend] Error adding user message: {e}")

    try:
        if req.model == "lora_sd":
            img_bytes = generate_image_lora(
                prompt=req.prompt,
                num_steps=req.num_steps,
                guidance_scale=req.guidance_scale,
                width=req.width,
                height=req.height,
                seed=req.seed,
            )
        elif req.model == "vae_gan":
            img_bytes = generate_image_gan(seed=req.seed)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

        # Save to disk + DB
        saved = save_generated_image(
            img_bytes, req.prompt, req.model, req.session_id
        )

        # Save assistant response to chat history
        if req.session_id:
            add_message(
                session_id=req.session_id,
                role='assistant',
                content=saved['filepath'],
                msg_type='image',
                prompt=req.prompt,
                model_used=req.model
            )

        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        enriched = enrich_prompt(req.prompt)

        return {
            "image_b64"   : img_b64,
            "filepath"    : saved['filepath'],
            "model_used"  : req.model,
            "enriched_prompt": enriched,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Image Captioning ─────────────────────────────────────────────────────────

@app.post("/caption")
def caption(req: CaptionRequest):
    """
    Caption an uploaded image using BLIP2.
    Optionally answer a question about the image.
    """
    try:
        img_bytes = base64.b64decode(req.image_b64)
        result    = caption_image(img_bytes, question=req.question)

        if req.session_id:
            add_message(
                session_id=req.session_id,
                role='assistant',
                content=result,
                msg_type='caption',
                model_used='blip2'
            )

        return {"caption": result, "model_used": "blip2"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/caption/upload")
async def caption_upload(
    file: UploadFile = File(...),
    session_id: Optional[int] = None,
    question: Optional[str] = None
):
    """Caption an image uploaded as multipart form data."""
    img_bytes = await file.read()
    img_b64   = base64.b64encode(img_bytes).decode('utf-8')
    req       = CaptionRequest(image_b64=img_b64, session_id=session_id, question=question)
    return caption(req)


# ── Chat (Gemini) ─────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest):
    """
    Astronomy QA chat using Gemini API.
    Supports multimodal (image + question).
    """
    try:
        history    = get_session_context(req.session_id, max_messages=8)
        image_bytes= base64.b64decode(req.image_b64) if req.image_b64 else None

        # Save user message to history
        add_message(
            session_id=req.session_id,
            role='user',
            content=req.message,
            msg_type='text'
        )

        response = ask_gemini(
            user_message=req.message,
            history=history,
            image_bytes=image_bytes
        )

        # Save assistant response to history
        add_message(
            session_id=req.session_id,
            role='assistant',
            content=response,
            msg_type='text',
            model_used='gemini'
        )

        return {"response": response, "model_used": "gemini"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Image Gallery ─────────────────────────────────────────────────────────────

@app.get("/gallery")
def gallery(limit: int = 50):
    """Return all generated images with base64 thumbnails."""
    images = get_all_generated_images(limit)
    result = []
    for img in images:
        img['thumbnail_b64'] = image_to_base64(img['filepath'])
        result.append(img)
    return result


# ── Settings (Gemini key, backend preference) ─────────────────────────────────

_ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
_STATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app_state.json')

def _read_env():
    """Read .env file as a dict."""
    env = {}
    try:
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, _, v = line.partition('=')
                        env[k.strip()] = v.strip().strip("'\"")
    except Exception:
        pass
    return env

def _write_env(updates: dict):
    """Write key=value pairs to .env, creating if missing."""
    env = _read_env()
    env.update(updates)
    try:
        with open(_ENV_PATH, 'w', encoding='utf-8') as f:
            for k, v in env.items():
                f.write(f"{k}={v}\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not write .env: {e}")

def _read_state():
    default = {"launch_count": 0, "kaggle_connected": False, "kaggle_url": ""}
    try:
        if os.path.exists(_STATE_PATH):
            import json
            with open(_STATE_PATH, 'r', encoding='utf-8') as f:
                return {**default, **json.load(f)}
    except Exception:
        pass
    return default

def _write_state(state: dict):
    import json
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        with open(_STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not write app_state: {e}")


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    backend: Optional[str] = None   # "cpu" | "cuda"


from fastapi.responses import RedirectResponse, HTMLResponse
import requests

def send_onboarding_email(email: str, name: str):
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if not resend_key:
        print("[Auth] RESEND_API_KEY not configured. Skipping email dispatch.")
        return
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "AstroGen Space Studio <onboarding@resend.dev>",
        "to": [email],
        "subject": "AstroGen Sign-in Successful!",
        "html": f"""
        <html>
        <body style="font-family: sans-serif; background-color: #040508; color: #ffffff; padding: 30px; border-radius: 12px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #1f2937; padding: 20px; border-radius: 8px; background-color: #080b18;">
                <h2 style="color: #6366f1; border-bottom: 1px solid #1f2937; padding-bottom: 10px;">✦ ASTROGEN SPACE STUDIO</h2>
                <p>Hello <strong>{name}</strong>,</p>
                <p>Welcome to AstroGen Space Studio! You have successfully signed in using Google.</p>
                <p>Your workspace, models, and deep-learning modules are now active and ready for your astronomical exploration.</p>
                <br>
                <hr style="border: 0; border-top: 1px solid #1f2937;">
                <p style="font-size: 11px; color: #64748b;">AstroGen Space Studio &bull; Local Desktop Instance</p>
            </div>
        </body>
        </html>
        """
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[Auth] Sent welcome email: Status={r.status_code}, Response={r.text}")
    except Exception as e:
        print(f"[Auth] Error sending welcome email: {e}")


@app.get("/settings")
def get_settings():
    """Return current settings (keys partially masked for security)."""
    env = _read_env()
    state = _read_state()
    key = env.get("GEMINI_API_KEY", "")
    kaggle_connected = state.get("kaggle_connected", False)
    # When Kaggle is connected, inference runs on the remote GPU regardless of local env
    effective_backend = "cuda" if kaggle_connected else env.get("ASTROGEN_BACKEND", "cpu")
    return {
        "gemini_api_key": key[:8] + "..." + key[-4:] if len(key) > 14 else ("set" if key else ""),
        "gemini_api_key_set": bool(key),
        "backend": effective_backend,
        "kaggle_connected": kaggle_connected,
        "kaggle_url": state.get("kaggle_url", ""),
        "launch_count": state.get("launch_count", 0),
        "kaggle_username": env.get("KAGGLE_USERNAME", ""),
        "kaggle_key_set": bool(env.get("KAGGLE_KEY", "")),
        "user_name": state.get("user_name", ""),
        "user_email": state.get("user_email", ""),
        "user_picture": state.get("user_picture", ""),
    }


@app.get("/auth/google")
def auth_google():
    """Redirect to Google OAuth consent page."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = "http://localhost:8001/auth/callback"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20profile%20email"
    )
    return RedirectResponse(url)


@app.get("/auth/callback")
def auth_callback(code: str):
    """Handle callback from Google and retrieve user credentials."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = "http://localhost:8001/auth/callback"

    # Exchange authorization code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    try:
        r = requests.post(token_url, data=data, timeout=10)
        tokens = r.json()
        access_token = tokens.get("access_token")
        if not access_token:
            return HTMLResponse("<h3>Authentication failed: No access token returned.</h3>")
            
        # Get user details from userinfo endpoint
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        info_resp = requests.get(userinfo_url, headers=headers, timeout=10)
        user_info = info_resp.json()
        
        user_name = user_info.get("name", "")
        user_email = user_info.get("email", "")
        user_picture = user_info.get("picture", "")
        
        # Save user to app state
        state = _read_state()
        state["user_name"] = user_name
        state["user_email"] = user_email
        state["user_picture"] = user_picture
        _write_state(state)
        
        # Save profile to Supabase PostgreSQL database if configured
        save_user_profile(user_email, user_name, user_picture, opt_in=True)
        
        # Send transactional welcome email
        send_onboarding_email(user_email, user_name)
        
        # Display a beautiful success page that instructs user they can return to AstroGen
        html_content = """
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background-color: #040508; color: #ffffff; text-align: center; padding-top: 100px;">
            <div style="max-width: 450px; margin: 0 auto; padding: 40px; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; background-color: #080b18; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);">
                <div style="font-size: 48px; color: #10b981; margin-bottom: 20px;">✓</div>
                <h2 style="margin-bottom: 10px; font-weight: 700; letter-spacing: 1px;">Signed In Successfully</h2>
                <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 30px;">
                    Welcome to AstroGen Space Studio. You may now close this browser tab and return to the application.
                </p>
                <div style="font-size: 11px; color: #475569;">ASTROGEN SPACE STUDIO</div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html_content)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h3>Authentication error: {str(e)}</h3>")


@app.post("/auth/logout")
def auth_logout():
    """Log user out by clearing user fields in app state."""
    state = _read_state()
    state.pop("user_name", None)
    state.pop("user_email", None)
    state.pop("user_picture", None)
    _write_state(state)
    return {"ok": True}



@app.post("/settings")
def update_settings(req: SettingsUpdate):
    """Save settings to .env."""
    updates = {}
    if req.gemini_api_key is not None and req.gemini_api_key.strip():
        updates["GEMINI_API_KEY"] = req.gemini_api_key.strip()
    if req.backend is not None and req.backend in ("cpu", "cuda"):
        updates["ASTROGEN_BACKEND"] = req.backend
    if updates:
        _write_env(updates)
    return {"ok": True, "updated": list(updates.keys())}


# ── Kaggle GPU URL & Auto-Launch management ──────────────────────────────────

class KaggleUrlRequest(BaseModel):
    url: str

class KaggleLaunchRequest(BaseModel):
    username: str
    key: str


@app.post("/kaggle/launch")
def launch_kaggle(req: KaggleLaunchRequest):
    """
    Launch the Kaggle GPU server.
    Saves username and key to .env.
    Pushes launcher script to Kaggle.
    Returns session_token.
    """
    try:
        # Save credentials to .env
        _write_env({
            "KAGGLE_USERNAME": req.username.strip(),
            "KAGGLE_KEY": req.key.strip()
        })
        
        # Read Gemini API key to bake into the launcher
        env = _read_env()
        gemini_key = env.get("GEMINI_API_KEY", "")
        
        import importlib
        import kaggle_launch
        importlib.reload(kaggle_launch)
        token = kaggle_launch.launch_kaggle_server(
            username=req.username.strip(),
            key=req.key.strip(),
            gemini_key=gemini_key
        )
        return {"ok": True, "session_token": token}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kaggle/poll")
def poll_kaggle(token: str, username: Optional[str] = None, key: Optional[str] = None):
    """
    Poll key-value store for the Kaggle server URL.
    Also checks status of the Kaggle kernel if URL isn't ready.
    """
    import kaggle_launch
    url = kaggle_launch.get_kaggle_url(token)
    if url:
        # Auto-connect and save it!
        _write_env({"AZURE_API_URL": url})
        state = _read_state()
        state["kaggle_url"] = url
        state["kaggle_connected"] = True
        _write_state(state)
        return {"status": "success", "url": url}
        
    # Check remote status if credentials are provided or in env
    status = "unknown"
    if username and key:
        status = kaggle_launch.check_kernel_status(username, key)
    else:
        env = _read_env()
        u = env.get("KAGGLE_USERNAME", "")
        k = env.get("KAGGLE_KEY", "")
        if u and k:
            status = kaggle_launch.check_kernel_status(u, k)
            
    status_lower = status.lower()
    if "error" in status_lower or status_lower in ("complete", "stopped", "hasfailed", "cancel_requested", "cancel_acknowledged"):
        return {"status": "failed", "detail": f"Kaggle kernel status: {status}"}
        
    return {"status": "waiting", "detail": f"Server status: {status}"}


@app.get("/kaggle/status")
def kaggle_status():
    """Check if a Kaggle GPU URL is configured and reachable."""
    import json
    env = _read_env()
    state = _read_state()
    url = env.get("AZURE_API_URL", "") or state.get("kaggle_url", "")
    if not url:
        return {"connected": False, "url": "", "reachable": False}

    # Quick connectivity test — remote Kaggle backend exposes /status not /health
    reachable = False
    for endpoint in ["/status", "/health"]:
        try:
            import requests as _req
            resp = _req.get(f"{url.rstrip('/')}{endpoint}", timeout=8)
            if resp.status_code == 200:
                reachable = True
                break
        except Exception:
            continue

    return {"connected": True, "url": url, "reachable": reachable}


@app.post("/kaggle/url")
def set_kaggle_url(req: KaggleUrlRequest):
    """Save a Kaggle GPU backend URL (Pinggy / ngrok tunnel)."""
    url = req.url.strip().rstrip("/")
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    # Save to both .env (for models.py) and app_state.json
    _write_env({"AZURE_API_URL": url})
    state = _read_state()
    state["kaggle_url"] = url
    state["kaggle_connected"] = True
    _write_state(state)

    # Reload env in models module
    try:
        import importlib, backend.models as _models
        importlib.reload(_models)
    except Exception:
        pass

    return {"ok": True, "url": url}


@app.delete("/kaggle/url")
def clear_kaggle_url():
    """Disconnect Kaggle GPU — revert to local CPU."""
    _write_env({"AZURE_API_URL": ""})
    state = _read_state()
    state["kaggle_url"] = ""
    state["kaggle_connected"] = False
    _write_state(state)
    return {"ok": True, "message": "Kaggle GPU disconnected. Using local CPU."}


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AstroGen Backend starting...")
    print("  API: http://localhost:8001")
    print("  Docs: http://localhost:8001/docs")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

