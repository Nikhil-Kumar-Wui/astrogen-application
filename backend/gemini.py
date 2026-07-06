"""
AstroGen — gemini.py
Free Gemini API integration for:
  - General astronomy QA (questions outside model scope)
  - Chat fallback when no image/generation is needed
  - Context-aware multi-turn astronomy conversation
"""

import os
import base64
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSISTENT_DIR = os.path.join(os.getenv('APPDATA'), 'AstroGen') if (getattr(sys, 'frozen', False) and os.name == 'nt' and os.getenv('APPDATA')) else PROJECT_ROOT
os.makedirs(PERSISTENT_DIR, exist_ok=True)
load_dotenv(os.path.join(PERSISTENT_DIR, '.env'))

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

SYSTEM_PROMPT = """You are AstroGen, an expert astronomy AI assistant. 
You have deep knowledge of:
- Astronomical objects: galaxies, nebulae, stars, planets, black holes, quasars
- Space missions: NASA, ESA, JWST, Hubble, Voyager, Mars rovers
- Astrophysics: stellar evolution, cosmology, dark matter, gravitational waves  
- Space imagery: how astronomers capture and process images, false color, wavelengths
- The APOD (Astronomy Picture of the Day) archive

When answering:
- Be enthusiastic and engaging about space
- Use accurate scientific terminology but explain it clearly
- If discussing an image, be specific about what astronomical features you observe
- Keep responses concise but informative (2-4 paragraphs max)
- If asked something outside astronomy, gently redirect to space topics

You are part of a desktop app that generates and analyzes space images using AI models 
fine-tuned on NASA data. Users may ask about generated images or general astronomy."""


def ask_gemini(
    user_message: str,
    history: list = None,
    image_bytes: bytes = None,
) -> str:
    """
    Send message to Gemini API.

    Args:
        user_message: User's text input
        history: List of {'role': str, 'content': str} for context
        image_bytes: Optional image bytes for multimodal query

    Returns:
        Gemini response string, or error message if API unavailable
    """
    if not GEMINI_API_KEY:
        return ("⚠ Gemini API key not set. Add GEMINI_API_KEY to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/\n\n"
                "I can still generate images and caption them with the local models!")

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        model_name = 'gemini-2.5-flash'
        model      = genai.GenerativeModel(
            model_name,
            system_instruction=SYSTEM_PROMPT
        )

        # Build message content
        if image_bytes:
            # Multimodal: image + text
            import PIL.Image
            import io
            img = PIL.Image.open(io.BytesIO(image_bytes))
            contents = [img, user_message]
        else:
            contents = [user_message]

        # Add conversation history context
        if history:
            chat = model.start_chat(history=[
                {'role': h['role'], 'parts': [h['content']]}
                for h in history[-8:]  # last 8 messages for context
                if h['role'] in ['user', 'model']
            ])
            response = chat.send_message(contents)
        else:
            response = model.generate_content(contents)

        return response.text

    except ImportError:
        return ("⚠ google-generativeai not installed. Run:\n"
                "pip install google-generativeai")

    except Exception as e:
        err_str = str(e)
        if 'API_KEY' in err_str or '401' in err_str:
            return "⚠ Invalid Gemini API key. Check your .env file."
        elif 'quota' in err_str.lower() or '429' in err_str:
            return "⚠ Gemini rate limit reached. Wait a moment and try again."
        else:
            return f"⚠ Gemini error: {err_str[:200]}"


def is_gemini_available() -> bool:
    """Check if Gemini API is configured."""
    return bool(GEMINI_API_KEY)
