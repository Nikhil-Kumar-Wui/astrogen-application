import os
import json
import uuid
import shutil

os.environ["KAGGLE_USERNAME"] = "nikhilkumarwui"
os.environ["KAGGLE_KEY"] = "5c80d73de51f77ef9d657108d99e34ae"

from kaggle.api.kaggle_api_extended import KaggleApi

project_root = "c:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT"
temp_dir = os.path.join(project_root, "data", "temp_kaggle_test")
os.makedirs(temp_dir, exist_ok=True)

# Generate dummy launch.py and metadata
meta = {
    "id": "nikhilkumarwui/astrogen-gpu-launcher",
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

with open(os.path.join(temp_dir, "launch.py"), "w", encoding="utf-8") as f:
    f.write("print('Test push')\n")

api = KaggleApi()
api.authenticate()
try:
    print("Pushing kernel...")
    res = api.kernels_push(temp_dir)
    print("Push result:", repr(res))
    # Check attributes of result
    if res:
        print("Fields in push response:", dir(res))
        print("url:", getattr(res, "url", None))
        print("error:", getattr(res, "error", None))
except Exception as e:
    print("Push error:", e)
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
