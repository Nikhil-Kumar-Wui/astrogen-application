"""
AstroGen Model Uploader
Uploads models to https://huggingface.co/nik-nikhil-wui/AstroGen-Models
"""
import os
import sys
from huggingface_hub import HfApi, login

# ── Config ──────────────────────────────────────────────────────────────
HF_TOKEN  = "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"
REPO_ID   = "nik-nikhil-wui/AstroGen-Models"
REPO_TYPE = "model"

PROJECT_ROOT = r"C:\Users\harsh\Desktop\NTCC - In House\APPLICATION\APP 5\PROJECT"
MODELS_DIR   = os.path.join(PROJECT_ROOT, "models")

# ── Files/folders to SKIP (not needed for inference) ─────────────────────
SKIP_FILES = {
    "lora_epoch1.safetensors",
    "lora_epoch2.safetensors",
    "lora_epoch3.safetensors",
    "lora_epoch4.safetensors",
    "results (3).zip",
    "training_log.json",
    "eval_metrics.json",
    "discriminator.pt",          # not used for image generation
    "blip2_eval_metrics.json",
    "blip2_train_log.json",
}

SKIP_DIRS = {
    "checkpoints",               # intermediate training checkpoints
}

# ──────────────────────────────────────────────────────────────────────────
def log(msg):
    print(msg, flush=True)

def main():
    log("=" * 60)
    log("  AstroGen -> HuggingFace Uploader")
    log(f"  Repo: {REPO_ID}")
    log("=" * 60)

    # Login
    log("\n[1/5] Logging in to Hugging Face...")
    login(token=HF_TOKEN, add_to_git_credential=False)
    api = HfApi()
    log("      [OK] Logged in successfully")

    # ── Upload astrogen_merged (full SD pipeline) ──────────────────────
    log("\n[2/5] Uploading astrogen_merged (merged Stable Diffusion pipeline)...")
    src = os.path.join(MODELS_DIR, "astrogen_merged")
    if os.path.isdir(src):
        api.upload_folder(
            folder_path=src,
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            path_in_repo="astrogen_merged",
        )
        log("      [OK] astrogen_merged uploaded")
    else:
        log("      [SKIP] astrogen_merged folder not found, skipping")

    # ── Upload LoRA final weights ──────────────────────────────────────
    log("\n[3/5] Uploading LoRA weights (astrogen_lora.safetensors)...")
    lora_file = os.path.join(MODELS_DIR, "lora", "astrogen_lora.safetensors")
    if os.path.isfile(lora_file):
        api.upload_file(
            path_or_fileobj=lora_file,
            path_in_repo="lora/astrogen_lora.safetensors",
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
        )
        log("      [OK] astrogen_lora.safetensors uploaded")
    else:
        log("      [SKIP] astrogen_lora.safetensors not found, skipping")

    # ── Upload BLIP2 finetuned adapter ───────────────────────────────
    log("\n[4/5] Uploading BLIP2 finetuned adapter...")
    blip2_dir = os.path.join(MODELS_DIR, "blip2", "blip2_finetuned")
    if os.path.isdir(blip2_dir):
        api.upload_folder(
            folder_path=blip2_dir,
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            path_in_repo="blip2/blip2_finetuned",
        )
        log("      [OK] blip2_finetuned uploaded")
    else:
        log("      [SKIP] blip2_finetuned folder not found, skipping")

    # ── Upload VAE-GAN weights (encoder + generator only) ────────────
    log("\n[5/5] Uploading VAE-GAN weights (encoder.pt + generator.pt)...")
    for fname in ["encoder.pt", "generator.pt"]:
        fpath = os.path.join(MODELS_DIR, "vae_gan", fname)
        if os.path.isfile(fpath):
            size_mb = os.path.getsize(fpath) / (1024*1024)
            log(f"      Uploading {fname} ({size_mb:.0f} MB)...")
            api.upload_file(
                path_or_fileobj=fpath,
                path_in_repo=f"vae_gan/{fname}",
                repo_id=REPO_ID,
                repo_type=REPO_TYPE,
            )
            log(f"      [OK] {fname} uploaded")
        else:
            log(f"      [SKIP] {fname} not found, skipping")

    log("\n" + "=" * 60)
    log("  [DONE] All uploads complete!")
    log(f"  View repo: https://huggingface.co/{REPO_ID}")
    log("=" * 60)

if __name__ == "__main__":
    main()
