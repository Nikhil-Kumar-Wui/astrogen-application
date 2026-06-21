import os
import sys
import uuid
import zipfile
import io
import base64
import shutil
import json
import requests

def pack_backend_to_zip_b64():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_pack = ["main.py", "models.py", "database.py", "gemini.py"]
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in files_to_pack:
            fpath = os.path.join(backend_dir, fname)
            if os.path.exists(fpath):
                z.write(fpath, arcname=f"backend/{fname}")
                
    zip_buffer.seek(0)
    return base64.b64encode(zip_buffer.read()).decode("utf-8")

def generate_launch_script(zip_b64, session_token, gemini_key="", hf_token=""):
    script = f"""# AstroGen GPU Launcher
import base64
import zipfile
import io
import os
import subprocess
import re
import time
import urllib.request
import json

print("[AstroGen] Initializing GPU backend...")

# 1. Write backend files
zip_b64 = "{zip_b64}"
os.makedirs("/kaggle/working", exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(zip_b64))) as z:
    z.extractall("/kaggle/working")
print("[AstroGen] Unzipped backend files.")

# 2. Write environment variables (.env)
with open("/kaggle/working/.env", "w", encoding="utf-8") as f:
    f.write("ASTROGEN_BACKEND=cuda\\n")
    f.write("GEMINI_API_KEY={gemini_key}\\n")
    f.write("HF_API_TOKEN={hf_token}\\n")
print("[AstroGen] Environment configured.")

# 3. Install dependencies
print("[AstroGen] Installing libraries...")
subprocess.run(
    ["pip", "install", "-q", "fastapi", "uvicorn", "python-multipart", "pydantic", "peft==0.9.0", "accelerate==0.27.2", "transformers==4.38.2", "google-generativeai", "requests", "huggingface_hub"],
    check=True
)
print("[AstroGen] Libraries installed.")

# 4. Download AstroGen models from HuggingFace
print("[AstroGen] Downloading models from HuggingFace...")
try:
    from huggingface_hub import hf_hub_download, snapshot_download
    HF_REPO = "nik-nikhil-wui/AstroGen-Models"
    HF_TOKEN = "{hf_token}"
    MODELS_DIR = "/kaggle/working/models"
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 4a. Full merged SD pipeline (unet, vae, tokenizer, text_encoder, scheduler, feature_extractor)
    print("[AstroGen] Downloading astrogen_merged SD pipeline...")
    snapshot_download(
        repo_id=HF_REPO,
        allow_patterns=["astrogen_merged/**"],
        local_dir=MODELS_DIR,
        token=HF_TOKEN,
    )
    print("[AstroGen] astrogen_merged downloaded.")

    # 4b. Final LoRA weights
    print("[AstroGen] Downloading LoRA weights...")
    os.makedirs(f"{{MODELS_DIR}}/lora", exist_ok=True)
    hf_hub_download(
        repo_id=HF_REPO,
        filename="lora/astrogen_lora.safetensors",
        local_dir=MODELS_DIR,
        token=HF_TOKEN,
    )
    print("[AstroGen] LoRA weights downloaded.")

    # 4c. BLIP2 finetuned adapter
    print("[AstroGen] Downloading BLIP2 adapter...")
    snapshot_download(
        repo_id=HF_REPO,
        allow_patterns=["blip2/blip2_finetuned/**"],
        local_dir=MODELS_DIR,
        token=HF_TOKEN,
    )
    print("[AstroGen] BLIP2 adapter downloaded.")

    # 4d. VAE-GAN encoder + generator
    print("[AstroGen] Downloading VAE-GAN weights...")
    os.makedirs(f"{{MODELS_DIR}}/vae_gan", exist_ok=True)
    for fname in ["encoder.pt", "generator.pt"]:
        hf_hub_download(
            repo_id=HF_REPO,
            filename=f"vae_gan/{{fname}}",
            local_dir=MODELS_DIR,
            token=HF_TOKEN,
        )
    print("[AstroGen] VAE-GAN weights downloaded.")

    print("[AstroGen] All models ready.")
except Exception as e:
    print(f"[AstroGen] WARNING: Model download failed: {{e}}")
    print("[AstroGen] Continuing - backend will attempt local model load.")

# 5. Launch backend process
log_file = open("/kaggle/working/backend_log.txt", "w")
backend_proc = subprocess.Popen(
    ["python", "-u", "/kaggle/working/backend/main.py"],
    stdout=log_file,
    stderr=subprocess.STDOUT
)
print("[AstroGen] Backend server started.")

# 6. Start Tunnel (tries multiple options)
print("[AstroGen] Starting Tunnel...")
tunnel_url = None
tunnels_to_try = [
    ["ssh", "-o", "StrictHostKeyChecking=no", "-p", "443", "-R0:localhost:8001", "qr@free.pinggy.io"],
    ["ssh", "-o", "StrictHostKeyChecking=no", "-p", "443", "-R0:localhost:8001", "qr@pinggy.io"],
    ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8001", "nokey@localhost.run"],
    ["ssh", "-o", "StrictHostKeyChecking=no", "-p", "80", "-R0:localhost:8001", "qr@free.pinggy.io"],
    ["ssh", "-o", "StrictHostKeyChecking=no", "-R0:localhost:8001", "qr@free.pinggy.io"]
]

active_proc = None
for idx, cmd in enumerate(tunnels_to_try):
    print(f"[AstroGen] Trying tunnel: {{' '.join(cmd)}}")
    log_path = f"/kaggle/working/tunnel_{{idx}}.log"
    try:
        out_f = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=out_f,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Read log file with timeout
        start_time = time.time()
        matched = False
        while time.time() - start_time < 15:
            if proc.poll() is not None:
                break
            time.sleep(1.0)
            
            # Read current content of log file
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                urls = re.findall(r"https://[a-zA-Z0-9.-]+\\.(?:pinggy\\.link|localhost\\.run|lhr\\.life|lhrtunnel\\.link)", content)
                valid_url = None
                for u in urls:
                    u_lower = u.lower()
                    if "admin.localhost.run" in u_lower or "dashboard" in u_lower:
                        continue
                    valid_url = u
                    break
                if valid_url:
                    tunnel_url = valid_url
                    print(f"\\n[AstroGen] SUCCESS: Tunnel URL is {{tunnel_url}}\\n")
                    matched = True
                    break
                    
        out_f.close()
        if matched:
            active_proc = proc
            break
        else:
            print("[AstroGen] Tunnel command timed out or failed. Trying next...")
            proc.terminate()
            proc.wait()
    except Exception as e:
        print(f"[AstroGen] Failed to launch tunnel: {{e}}")

if not tunnel_url:
    print("[AstroGen] ERROR: All tunnel attempts failed.")
    os._exit(1)

# 7. Report URL to key-value store
token = "{session_token}"
url_reported = False
encoded_url = base64.b64encode(tunnel_url.encode()).decode()
for attempt in range(5):
    try:
        api_url = f"https://keyvalue.immanuel.co/api/keyval/UpdateValue/astrogen_studio/token_{{token}}/{{encoded_url}}"
        req = urllib.request.Request(api_url, method="POST")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                print(f"[AstroGen] URL reported successfully on attempt {{attempt+1}}.")
                url_reported = True
                break
    except Exception as e:
        print(f"[AstroGen] Report attempt {{attempt+1}} failed: {{e}}")
        time.sleep(2)

# Keep running
try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    pass
"""
    return script

def launch_kaggle_server(username, key, gemini_key=""):
    session_token = uuid.uuid4().hex[:12]

    # Read HuggingFace read token from local .env
    hf_token = ""
    try:
        project_root_env = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root_env, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if line.startswith("HF_API_TOKEN="):
                        hf_token = line.split("=", 1)[1].strip()
                        break
    except Exception:
        pass

    # Setup temporary directory inside data
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(project_root, "data", f"temp_kaggle_{session_token}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 2. Write metadata.json
        meta = {
            "id": f"{username.lower()}/astrogen-gpu-launcher",
            "title": "AstroGen GPU Launcher",
            "code_file": "launch.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "enable_internet": True,
            "machine_shape": "NvidiaTeslaT4",
            "dataset_sources": [],
            "kernel_sources": [],
            "competition_sources": []
        }
        with open(os.path.join(temp_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        # 3. Write launch.py (pass hf_token so Kaggle can pull models from HuggingFace)
        zip_b64 = pack_backend_to_zip_b64()
        script_code = generate_launch_script(zip_b64, session_token, gemini_key, hf_token)
        with open(os.path.join(temp_dir, "launch.py"), "w", encoding="utf-8") as f:
            f.write(script_code)
            
        # 4. Authenticate and push using KaggleApi
        os.environ["KAGGLE_USERNAME"] = username
        os.environ["KAGGLE_KEY"] = key
        
        user_home = os.path.expanduser("~")
        dot_kaggle = os.path.join(user_home, ".kaggle")
        os.makedirs(dot_kaggle, exist_ok=True)
        with open(os.path.join(dot_kaggle, "kaggle.json"), "w", encoding="utf-8") as f:
            json.dump({"username": username, "key": key}, f)
            
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        # Push kernel
        res = api.kernels_push(temp_dir)
        if res and getattr(res, "error", None):
            raise RuntimeError(str(res.error))
        
    finally:
        # Clean up temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
            
    return session_token

def get_kaggle_url(session_token):
    try:
        api_url = f"https://keyvalue.immanuel.co/api/keyval/GetValue/astrogen_studio/token_{session_token}"
        resp = requests.get(api_url, timeout=5)
        if resp.status_code == 200:
            val = resp.text.strip().strip('"')
            if val and val != "null":
                # Decode base64 URL
                return base64.b64decode(val.encode()).decode()
    except Exception:
        pass
    return None

def check_kernel_status(username, key):
    try:
        os.environ["KAGGLE_USERNAME"] = username
        os.environ["KAGGLE_KEY"] = key
        
        user_home = os.path.expanduser("~")
        dot_kaggle = os.path.join(user_home, ".kaggle")
        os.makedirs(dot_kaggle, exist_ok=True)
        with open(os.path.join(dot_kaggle, "kaggle.json"), "w", encoding="utf-8") as f:
            json.dump({"username": username, "key": key}, f)
            
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        status_obj = api.kernels_status(f"{username}/astrogen-gpu-launcher")
        status_val = getattr(status_obj, "status", status_obj)
        if hasattr(status_val, "name"):
            return str(status_val.name)
        return str(status_val)
    except Exception as e:
        return f"error: {str(e)}"
