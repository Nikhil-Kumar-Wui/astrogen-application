"""
AstroGen — models.py
Loads trained models from disk. Handles:
  - LoRA fine-tuned Stable Diffusion 1.5  → text-to-image generation
  - VAE-GAN decoder                        → random space image generation
  - BLIP2 fine-tuned                       → image captioning/explanation
All models loaded lazily (only when first used) to save RAM.
ML packages (torch, diffusers) are optional — backend starts without them.
"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
import io
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Optional ML imports (backend runs without them) ───────────────────────────
try:
    import torch
    import numpy as np
    from PIL import Image
    _ML_AVAILABLE = True
    print("[Models] ML packages available (torch, numpy, PIL)")
except ImportError as _e:
    _ML_AVAILABLE = False
    torch = None
    np    = None
    print(f"[Models] ML packages not installed ({_e}). "
          "Backend starts in no-model mode. "
          "Install torch/diffusers to enable image generation.")

# ── DNS-over-HTTPS patch for Hugging Face DNS resolution issues ──
try:
    import urllib.request
    import json
    import ssl
    import socket
    import sys

    def resolve_doh(hostname):
        try:
            url = f"https://8.8.8.8/resolve?name={hostname}&type=A"
            req = urllib.request.Request(
                url, 
                headers={"Accept": "application/dns-json"}
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=3.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                if "Answer" in data:
                    for ans in data["Answer"]:
                        if ans["type"] == 1: # A record
                            return ans["data"]
        except Exception as e:
            print(f"[Models] DoH resolution failed: {e}")
        return None

    orig_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(host, port, *args, **kwargs):
        if host and (host == "router.huggingface.co" or host.endswith(".huggingface.co")):
            ip = resolve_doh(host)
            if ip:
                print(f"[Models] Patched socket.getaddrinfo: {host} -> {ip}")
                return orig_getaddrinfo(ip, port, *args, **kwargs)
        return orig_getaddrinfo(host, port, *args, **kwargs)

    # Patch socket module
    socket.getaddrinfo = patched_getaddrinfo

    # Deep scan loaded modules to patch bound references
    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        try:
            if hasattr(mod, 'getaddrinfo') and mod.getaddrinfo == orig_getaddrinfo:
                mod.getaddrinfo = patched_getaddrinfo
            if hasattr(mod, 'socket') and getattr(mod.socket, 'getaddrinfo', None) == orig_getaddrinfo:
                mod.socket.getaddrinfo = patched_getaddrinfo
        except Exception:
            pass

    print("[Models] DNS-over-HTTPS fallback adapter loaded (deep socket patch applied).")
except Exception as e:
    print(f"[Models] Could not initialize DoH adapter: {e}")

# ── Paths ───────────────────────────────────────────────────────────────────
APP_DIR    = os.path.dirname(os.path.dirname(__file__))
MODELS_DIR = os.path.join(APP_DIR, 'models')

LORA_WEIGHTS_PATH  = os.path.join(MODELS_DIR, 'lora', 'astrogen_lora.safetensors')
GAN_ENC_PATH       = os.path.join(MODELS_DIR, 'vae_gan', 'encoder.pt')
GAN_GEN_PATH       = os.path.join(MODELS_DIR, 'vae_gan', 'generator.pt')
BLIP2_PATH         = os.path.join(MODELS_DIR, 'blip2', 'blip2_finetuned')

SD_BASE_MODEL      = 'runwayml/stable-diffusion-v1-5'
BLIP2_BASE_MODEL   = 'Salesforce/blip2-opt-2.7b'

def get_optimal_device():
    """Detect best available device: NVIDIA CUDA → CPU. No XPU/DirectML."""
    if not _ML_AVAILABLE:
        return 'cpu'
    backend_pref = os.getenv("ASTROGEN_BACKEND", "").strip().lower()
    if backend_pref == "cpu":
        print("[Models] ASTROGEN_BACKEND=cpu. Using CPU mode.")
        return 'cpu'
    if torch.cuda.is_available():
        print("[Models] NVIDIA CUDA detected!")
        return 'cuda'
    print("[Models] No CUDA GPU found. Using CPU mode.")
    return 'cpu'

DEVICE = get_optimal_device()
print(f"[Models] Active Device: {DEVICE}")

# ── No DirectML / XPU patches needed (NVIDIA CUDA + CPU only) ─────────────

# ── Astronomy Ontology (copy from notebook for prompt enrichment) ───────────
ASTRONOMY_ONTOLOGY = {
    'galaxy'   : {'style_tokens': 'astrophotography, deep field, NASA image'},
    'nebula'   : {'style_tokens': 'Hubble space telescope, false color, NASA image'},
    'star'     : {'style_tokens': 'astronomical observation, telescope image'},
    'planet'   : {'style_tokens': 'NASA spacecraft image, planetary science'},
    'sun'      : {'style_tokens': 'SDO image, solar dynamics observatory, UV wavelength'},
    'aurora'   : {'style_tokens': 'night sky photography, long exposure, vibrant colors'},
    'comet'    : {'style_tokens': 'astronomical photography, NASA APOD'},
    'deep_sky' : {'style_tokens': 'James Webb Space Telescope, JWST, deep field'},
}

SPACE_KEYWORDS = list(ASTRONOMY_ONTOLOGY.keys())


def detect_category(prompt: str) -> str:
    """Auto-detect astronomical category from user prompt."""
    prompt_lower = prompt.lower()
    for cat in SPACE_KEYWORDS:
        if cat in prompt_lower:
            return cat
    # Extra keyword mapping
    keyword_map = {
        'spiral': 'galaxy', 'andromeda': 'galaxy', 'milky way': 'galaxy',
        'orion': 'nebula', 'crab': 'nebula', 'pillars': 'nebula',
        'sunspot': 'sun', 'corona': 'sun', 'flare': 'sun',
        'mars': 'planet', 'saturn': 'planet', 'jupiter': 'planet',
        'northern lights': 'aurora', 'borealis': 'aurora',
        'jwst': 'deep_sky', 'hubble': 'deep_sky', 'webb': 'deep_sky',
    }
    for kw, cat in keyword_map.items():
        if kw in prompt_lower:
            return cat
    return 'deep_sky'  # default


def enrich_prompt(raw_prompt: str) -> str:
    """Add astronomy ontology style tokens to prompt."""
    cat  = detect_category(raw_prompt)
    ont  = ASTRONOMY_ONTOLOGY.get(cat, {})
    style= ont.get('style_tokens', 'NASA APOD, astronomy, high resolution')
    return f"{raw_prompt}. {style}"


# ── Lazy-loaded model registry ───────────────────────────────────────────────
_lora_pipeline  = None
_gan_decoder    = None
_blip2_model    = None
_blip2_processor= None


def get_model_status() -> dict:
    """Check which model weights are available on disk."""
    return {
        'lora_sd'     : os.path.exists(LORA_WEIGHTS_PATH),
        'vae_gan'     : os.path.exists(GAN_GEN_PATH),
        'blip2'       : os.path.exists(BLIP2_PATH),
        'device'      : str(DEVICE),
        'ml_packages' : _ML_AVAILABLE,
    }


# ── LoRA Stable Diffusion ───────────────────────────────────────────────────

def _load_lora_pipeline():
    global _lora_pipeline
    if not _ML_AVAILABLE:
        raise RuntimeError(
            "torch/diffusers not installed. "
            "Run: pip install torch diffusers transformers safetensors"
        )
    if _lora_pipeline is not None:
        return _lora_pipeline

    print("[Models] Loading LoRA-SD pipeline...")
    from diffusers import StableDiffusionPipeline
    from safetensors.torch import load_file

    dtype = torch.float16 if DEVICE == 'cuda' else torch.float32
    merged_path = os.path.join(MODELS_DIR, 'astrogen_merged')

    if os.path.exists(merged_path):
        print(f"[Models] Loading merged model from: {merged_path}")
        pipeline = StableDiffusionPipeline.from_pretrained(
            merged_path, torch_dtype=dtype, safety_checker=None
        )
    else:
        pipeline = StableDiffusionPipeline.from_pretrained(
            SD_BASE_MODEL, torch_dtype=dtype, safety_checker=None
        )
        if os.path.exists(LORA_WEIGHTS_PATH):
            print(f"[Models] Loading LoRA weights: {LORA_WEIGHTS_PATH}")
            lora_state = load_file(LORA_WEIGHTS_PATH)
            pipeline.unet.load_state_dict(lora_state, strict=False)
            print("[Models] LoRA weights loaded ✓")
        else:
            print("[Models] LoRA weights not found - using base SD 1.5")

    pipeline.to(DEVICE)
    pipeline.enable_attention_slicing()

    _lora_pipeline = pipeline
    return pipeline


def generate_image_lora(
    prompt: str,
    negative_prompt: str = "blurry, low quality, text, watermark, logo",
    num_steps: int = 30,
    guidance_scale: float = 7.5,
    width: int = 512,
    height: int = 512,
    seed: int = None,
) -> bytes:
    """
    Generate astronomical image from text prompt using LoRA fine-tuned SD.
    Returns PNG bytes.
    """
    # Check for Azure API URL for fast cloud GPU generation
    azure_url = os.getenv("AZURE_API_URL")
    if azure_url:
        azure_url = azure_url.strip("'\"")
        print(f"[Models] AZURE_API_URL detected. Delegating generation to Azure: {azure_url}...")
        try:
            import requests
            api_url = f"{azure_url.rstrip('/')}/generate"
            payload = {
                "prompt": prompt,
                "model": "lora_sd",
                "session_id": None,
                "num_steps": num_steps,
                "guidance_scale": guidance_scale,
                "width": width,
                "height": height,
                "seed": seed
            }
            response = requests.post(api_url, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                img_b64 = data.get("image_b64")
                if img_b64:
                    print("[Models] Successfully generated image via Azure API!")
                    import base64
                    return base64.b64decode(img_b64)
                else:
                    print(f"[Models] Azure API response missing image_b64: {data}")
            else:
                print(f"[Models] Azure API returned status {response.status_code}: {response.text}")
                print("[Models] Falling back to next generation option...")
        except Exception as e:
            print(f"[Models] Error calling Azure API: {e}")
            print("[Models] Falling back to next generation option...")

    # Check for Hugging Face Inference API Token for fast cloud GPU generation
    hf_token = os.getenv("HF_API_TOKEN")
    if hf_token:
        hf_token = hf_token.strip("'\"")
        print("[Models] HF_API_TOKEN detected. Using Hugging Face Serverless Inference API...")
        try:
            import requests
            api_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
            headers = {"Authorization": f"Bearer {hf_token}"}
            enriched = enrich_prompt(prompt)
            payload = {
                "inputs": enriched,
                "parameters": {
                    "negative_prompt": negative_prompt,
                    "num_inference_steps": min(num_steps, 50),
                    "guidance_scale": guidance_scale,
                    "width": width,
                    "height": height,
                }
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=45)
            if response.status_code == 200:
                print("[Models] Successfully generated image via Hugging Face API!")
                return response.content
            else:
                print(f"[Models] Hugging Face API returned status {response.status_code}: {response.text}")
                print("[Models] Falling back to local generation...")
        except Exception as e:
            print(f"[Models] Error calling Hugging Face API: {e}")
            print("[Models] Falling back to local generation...")

    pipeline = _load_lora_pipeline()
    enriched = enrich_prompt(prompt)

    generator = None
    if seed is not None:
        generator = torch.Generator(device=DEVICE).manual_seed(seed)

    ctx = torch.autocast('cuda') if DEVICE == 'cuda' else torch.no_grad()
    with ctx:
        result = pipeline(
            enriched,
            negative_prompt=negative_prompt,
            num_inference_steps=num_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        )

    img    = result.images[0]
    buf    = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# ── VAE-GAN ─────────────────────────────────────────────────────────────────

if _ML_AVAILABLE:
    class _DecoderStub(torch.nn.Module):
        """Minimal decoder matching v4 AstroGen VAE-GAN architecture.
        Trained with: latent_dim=512, img_size=512, base_ch=64, 5 upsampling blocks.
        """
        def __init__(self, latent_dim=512, base_ch=64, img_size=512):
            super().__init__()
            self.init_size = img_size // 32  # 512//32 = 16
            self.base_ch   = base_ch
            self.fc = torch.nn.Linear(latent_dim, base_ch*8 * self.init_size ** 2)
            layers = []
            ch_list = [base_ch*8, base_ch*8, base_ch*4, base_ch*4, base_ch*2, base_ch*2, base_ch, 3]
            strides = [2, 2, 2, 2, 2]
            for i in range(len(strides)):
                layers += [
                    torch.nn.BatchNorm2d(ch_list[i]),
                    torch.nn.ConvTranspose2d(ch_list[i], ch_list[i+1], 4, strides[i], 1),
                    torch.nn.ReLU(True) if i < len(strides)-1 else torch.nn.Tanh()
                ]
            self.net = torch.nn.Sequential(*layers)

        def forward(self, z):
            h = self.fc(z).view(-1, self.base_ch*8, self.init_size, self.init_size)
            return self.net(h)


def _load_gan_decoder():
    global _gan_decoder
    if not _ML_AVAILABLE:
        raise RuntimeError(
            "torch not installed. Run: pip install torch torchvision"
        )
    if _gan_decoder is not None:
        return _gan_decoder

    print("[Models] Loading VAE-GAN decoder (latent_dim=512, img_size=512)...")
    decoder = _DecoderStub(latent_dim=512, base_ch=64, img_size=512).to(DEVICE)

    if os.path.exists(GAN_GEN_PATH):
        state = torch.load(GAN_GEN_PATH, map_location=DEVICE)
        decoder.load_state_dict(state, strict=False)
        decoder.eval()
        print("[Models] VAE-GAN decoder loaded \u2713")
    else:
        print("[Models] GAN weights not found - random noise output")

    _gan_decoder = decoder
    return decoder


def generate_image_gan(seed: int = None) -> bytes:
    """
    Generate random astronomical image using VAE-GAN decoder.
    Returns PNG bytes.
    """
    decoder = _load_gan_decoder()

    if seed is not None:
        torch.manual_seed(seed)

    with torch.no_grad():
        z   = torch.randn(1, 512, device=DEVICE)  # latent_dim=512 matches trained weights
        out = decoder(z)
        img_tensor = (out.squeeze(0).clamp(-1, 1) + 1) / 2  # [-1,1] → [0,1]

    import torchvision.transforms as T
    img = T.ToPILImage()(img_tensor.cpu())
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# ── BLIP2 Captioning ────────────────────────────────────────────────────────

def _load_blip2():
    """
    Load BLIP2 with PEFT LoRA adapter.
    Architecture: Salesforce/blip2-opt-2.7b base + LoRA r=16 adapter.
    Requires transformers==4.38.2 (pinned in requirements_docker.txt).
    The BLIP2_PATH folder must contain PEFT adapter files (adapter_config.json, adapter_model.*).
    If not present, falls back to base model.
    """
    global _blip2_model, _blip2_processor
    if not _ML_AVAILABLE:
        raise RuntimeError(
            "torch/transformers not installed. Run: pip install torch transformers"
        )
    if _blip2_model is not None:
        return _blip2_model, _blip2_processor

    print("[Models] Loading BLIP2 (base + LoRA adapter)...")
    from transformers import Blip2Processor, Blip2ForConditionalGeneration
    import inspect as _inspect

    dtype = torch.float16 if DEVICE == 'cuda' else torch.float32

    # ── Compatibility patch for PEFT + transformers 4.38 ──────────────────
    # PEFT passes inputs_embeds=None to forward() which Blip2 doesn't accept.
    # Patch the class BEFORE from_pretrained so accelerate captures safe version.
    _orig_fwd   = Blip2ForConditionalGeneration.forward
    _valid_keys = set(_inspect.signature(_orig_fwd).parameters.keys()) - {'self'}
    def _safe_fwd(self, *args, **kwargs):
        return _orig_fwd(self, *args, **{k: v for k, v in kwargs.items() if k in _valid_keys})
    Blip2ForConditionalGeneration.forward = _safe_fwd
    print("[Models] BLIP2 forward patch applied (PEFT compatibility).")

    # ── Load processor ───────────────────────────────────────────────────────
    # Always load processor from base model (adapter folder may not have it)
    processor_path = BLIP2_PATH if os.path.exists(os.path.join(BLIP2_PATH, 'preprocessor_config.json')) else BLIP2_BASE_MODEL
    print(f"[Models] Loading processor from: {processor_path}")
    processor = Blip2Processor.from_pretrained(processor_path)

    # ── Load base model + apply LoRA adapter ─────────────────────────────────
    adapter_config = os.path.join(BLIP2_PATH, 'adapter_config.json')
    if os.path.exists(adapter_config):
        # Fine-tuned adapter exists → load base model, then apply adapter
        print(f"[Models] Loading base model: {BLIP2_BASE_MODEL}")
        print(f"[Models] Will apply LoRA adapter from: {BLIP2_PATH}")
        base_model = Blip2ForConditionalGeneration.from_pretrained(
            BLIP2_BASE_MODEL,
            torch_dtype=dtype,
            device_map='auto' if DEVICE == 'cuda' else None,
        )
        try:
            from peft import PeftModel
            model = PeftModel.from_pretrained(base_model, BLIP2_PATH)
            print("[Models] LoRA adapter applied via PeftModel ✓")
        except Exception as e:
            print(f"[Models] PeftModel load failed ({e}). Using base model only.")
            model = base_model
    elif os.path.exists(BLIP2_PATH) and os.path.isdir(BLIP2_PATH):
        # May be a full saved model (not PEFT format) — try loading directly
        print(f"[Models] Loading full model from: {BLIP2_PATH}")
        model = Blip2ForConditionalGeneration.from_pretrained(
            BLIP2_PATH,
            torch_dtype=dtype,
            device_map='auto' if DEVICE == 'cuda' else None,
        )
    else:
        # No local weights — use base model
        print(f"[Models] No local BLIP2 weights found. Loading base: {BLIP2_BASE_MODEL}")
        model = Blip2ForConditionalGeneration.from_pretrained(
            BLIP2_BASE_MODEL,
            torch_dtype=dtype,
            device_map='auto' if DEVICE == 'cuda' else None,
        )

    if DEVICE == 'cpu' and not hasattr(model, 'hf_device_map'):
        model = model.to(DEVICE)

    model.eval()
    print("[Models] BLIP2 loaded and ready ✓")

    _blip2_model     = model
    _blip2_processor = processor
    return model, processor


def caption_image(img_bytes: bytes, question: str = None) -> str:
    """
    Generate APOD-style caption OR answer question about image.
    Args:
        img_bytes: Raw image bytes (PNG/JPG)
        question:  If None, generate free caption. If str, do VQA.
    Returns: Generated text
    """
    model, processor = _load_blip2()
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

    dtype = torch.float16 if DEVICE == 'cuda' else torch.float32
    if question:
        prompt = f"Question: {question} Answer:"
        inputs = processor(images=img, text=prompt, return_tensors='pt').to(DEVICE, dtype=dtype)
    else:
        inputs = processor(images=img, return_tensors='pt').to(DEVICE, dtype=dtype)

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=200)

    caption = processor.decode(generated_ids[0], skip_special_tokens=True).strip()
    return caption
