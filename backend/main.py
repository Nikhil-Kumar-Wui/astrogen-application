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
    save_generated_image, get_all_generated_images, image_to_base64
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


@app.get("/settings")
def get_settings():
    """Return current settings (keys partially masked for security)."""
    env = _read_env()
    state = _read_state()
    key = env.get("GEMINI_API_KEY", "")
    return {
        "gemini_api_key": key[:8] + "..." + key[-4:] if len(key) > 14 else ("set" if key else ""),
        "gemini_api_key_set": bool(key),
        "backend": env.get("ASTROGEN_BACKEND", "cpu"),
        "kaggle_connected": state.get("kaggle_connected", False),
        "kaggle_url": state.get("kaggle_url", ""),
        "launch_count": state.get("launch_count", 0),
    }


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


# ── Kaggle GPU URL management ────────────────────────────────────────────────

class KaggleUrlRequest(BaseModel):
    url: str


@app.get("/kaggle/status")
def kaggle_status():
    """Check if a Kaggle GPU URL is configured and reachable."""
    import json
    env = _read_env()
    state = _read_state()
    url = env.get("AZURE_API_URL", "") or state.get("kaggle_url", "")
    if not url:
        return {"connected": False, "url": "", "reachable": False}

    # Quick connectivity test
    reachable = False
    try:
        import requests as _req
        resp = _req.get(f"{url.rstrip('/')}/health", timeout=5)
        reachable = (resp.status_code == 200)
    except Exception:
        pass

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

