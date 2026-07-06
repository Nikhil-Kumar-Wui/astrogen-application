import os
import sys
import uuid
import zipfile
import io
import base64
import shutil
import json
import requests
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSISTENT_DIR = os.path.join(os.getenv('APPDATA'), 'AstroGen') if (getattr(sys, 'frozen', False) and os.name == 'nt' and os.getenv('APPDATA')) else PROJECT_ROOT

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
    ["pip", "install", "-q", "fastapi", "uvicorn", "python-multipart", "pydantic", "peft>=0.17.0", "accelerate>=0.29.3", "transformers>=4.40.0", "diffusers>=0.27.2", "google-generativeai", "requests", "huggingface_hub"],
    check=True
)
print("[AstroGen] Libraries installed.")

# 4. Locate AstroGen models — try native mount first, then REST API fallback
print("[AstroGen] Locating AstroGen model files...")
try:
    import shutil, zipfile, tempfile, requests as _rq
    KAGGLE_INPUT_DIR = "/kaggle/input/astrogen-models-private"
    MODELS_WORK_DIR = "/kaggle/working/downloaded_models"

    # Private dataset fallback configuration
    _DEV_USER = "nikhilkumarwui"
    _DEV_KEY  = "753c5ecfa4c26f865ff577d95f253c29"
    _DS_SLUG  = "nikhilkumarwui/astrogen-models-private"

    def find_astrogen_merged(search_root):
        for dirpath, dirnames, filenames in os.walk(search_root):
            if os.path.basename(dirpath) == "astrogen_merged":
                return dirpath
            for d in dirnames:
                if d == "astrogen_merged":
                    return os.path.join(dirpath, d)
        return None

    def _do_streaming_download(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        url = "https://www.kaggle.com/api/v1/datasets/download/" + _DS_SLUG
        print("[AstroGen] Fetching dataset zip from: " + url)
        resp = _rq.get(url, auth=(_DEV_USER, _DEV_KEY), stream=True, timeout=600, verify=False)
        if resp.status_code != 200:
            raise RuntimeError("[AstroGen] Download HTTP " + str(resp.status_code) + ": " + resp.text[:300])
        print("[AstroGen] Streaming to disk...")
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip", dir=dest_dir)
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                downloaded = 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (50 * 1024 * 1024) < 65536:
                            print("[AstroGen] Downloaded " + str(downloaded // (1024*1024)) + " MB...")
            print("[AstroGen] Download done (" + str(downloaded // (1024*1024)) + " MB). Extracting...")
            with zipfile.ZipFile(tmp_path) as zf:
                zf.extractall(dest_dir)
            print("[AstroGen] Extracted to: " + dest_dir)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _symlink_models(models_parent):
        for target in ["/kaggle/working/models", "/kaggle/working/backend/models"]:
            try:
                if os.path.islink(target):
                    os.unlink(target)
                elif os.path.isdir(target):
                    import shutil as _sh
                    _sh.rmtree(target)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.symlink(models_parent, target)
                print("[AstroGen] [OK] Symlinked " + models_parent + " -> " + target)
            except Exception as se:
                print("[AstroGen] WARNING: Symlink to " + target + " failed: " + str(se))
        
        check1 = "/kaggle/working/models/astrogen_merged"
        check2 = "/kaggle/working/backend/models/astrogen_merged"
        print("[AstroGen] Verifying paths: working/models/astrogen_merged: " + str(os.path.exists(check1)) + ", backend/models/astrogen_merged: " + str(os.path.exists(check2)))

    # --- Strategy 1: Check native mount ---
    input_contents = os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else []
    print("[AstroGen] /kaggle/input/ contents: " + str(input_contents))

    merged_src = find_astrogen_merged(KAGGLE_INPUT_DIR)
    if not merged_src:
        merged_src = find_astrogen_merged("/kaggle/input")

    if merged_src:
        print("[AstroGen] [OK] Native mount found astrogen_merged at: " + merged_src)
        _symlink_models(os.path.dirname(merged_src))
    else:
        # --- Strategy 2: Fallback to Streaming Download ---
        print("[AstroGen] Native mount empty. Falling back to REST API download...")
        _do_streaming_download(MODELS_WORK_DIR)
        merged_src = find_astrogen_merged(MODELS_WORK_DIR)
        if merged_src:
            print("[AstroGen] [OK] Download found astrogen_merged at: " + merged_src)
            _symlink_models(os.path.dirname(merged_src))
        else:
            print("[AstroGen] [ERROR] astrogen_merged not found after download. Contents:")
            for root, dirs, files in os.walk(MODELS_WORK_DIR):
                depth = root.replace(MODELS_WORK_DIR, "").count(os.sep)
                if depth < 3:
                    print("  " * depth + os.path.basename(root) + "/")
except Exception as e:
    print(f"[AstroGen] WARNING: Error setting up models: {{e}}")


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
try:
    print("[AstroGen] Downloading cloudflared (TryCloudflare) for reliable tunneling...")
    subprocess.run(["wget", "-q", "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", "-O", "/kaggle/working/cloudflared"])
    subprocess.run(["chmod", "+x", "/kaggle/working/cloudflared"])
except Exception as e:
    print(f"[AstroGen] Could not download cloudflared: {{e}}")

tunnel_url = None
tunnels_to_try = [
    ["/kaggle/working/cloudflared", "tunnel", "--url", "http://localhost:8001"],
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
                urls = re.findall(r"https://[a-zA-Z0-9.-]+\\.(?:pinggy\\.link|localhost\\.run|lhr\\.life|lhrtunnel\\.link|trycloudflare\\.com)", content)
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
        env_path = os.path.join(PERSISTENT_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if line.startswith("HF_API_TOKEN="):
                        hf_token = line.split("=", 1)[1].strip()
                        break
    except Exception:
        pass

    # Setup temporary directory inside writable PERSISTENT_DIR/data
    temp_dir = os.path.join(PERSISTENT_DIR, "data", f"temp_kaggle_{session_token}")
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
            "dataset_sources": ["nikhilkumarwui/astrogen-models-private"],
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
