# AstroGen Desktop App — Setup Guide

## Project Structure
```
app/
├── backend/
│   ├── main.py           ← FastAPI server (run this first)
│   ├── models.py         ← Model loading + inference
│   ├── database.py       ← SQLite chat history
│   └── gemini.py         ← Gemini API fallback QA
├── frontend/
│   └── main.py           ← PyQt6 desktop app (run after backend)
├── models/               ← Put your saved .safetensors/.pt files here
│   ├── lora/
│   │   └── astrogen_lora.safetensors
│   ├── vae_gan/
│   │   ├── encoder.pt
│   │   └── generator.pt
│   └── blip2/
│       └── blip2_finetuned/
├── assets/
│   └── icons/
├── requirements.txt
└── run.bat               ← Double-click to launch on Windows 11
```

## Setup (Windows 11)

### 1. Install Python 3.10+
Download from https://python.org — tick "Add to PATH"

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Copy model weights
After training in Colab, download from Google Drive and place in `models/` folder.

### 4. Set Gemini API Key
Create a `.env` file in the `app/` folder:
```
GEMINI_API_KEY=your_key_here
```
Get free key at: https://aistudio.google.com/

### 5. Launch
Double-click `run.bat`  
OR run manually:
```
# Terminal 1 — Backend
cd backend
python main.py

# Terminal 2 — Frontend  
cd frontend
python main.py
```

## Notes
- Backend runs on http://localhost:8000
- Chat history saved to app/data/astrogen.db (SQLite, local only)
- Generated images saved to app/data/generated/
- No internet required after setup (except Gemini QA feature)
