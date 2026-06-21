#!/bin/bash
set -e

MODELS_DIR="/app/models"
mkdir -p "$MODELS_DIR"

if [ ! -d "$MODELS_DIR/astrogen_merged" ]; then
    echo "[STARTUP] Downloading AstroGen merged model from Hugging Face..."
    python -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id='nik-nikhil-wui/astrogen-sd15-lora',
    local_dir='$MODELS_DIR/astrogen_merged',
    token=os.environ.get('HF_API_TOKEN'),
)
"
    echo "[STARTUP] Merged model downloaded successfully"
fi

echo "[STARTUP] Starting AstroGen API..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
