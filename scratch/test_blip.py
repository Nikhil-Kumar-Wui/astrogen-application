import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

import io
import torch
from PIL import Image
from models import _load_blip2

# Create a dummy image
img = Image.new('RGB', (224, 224), color='blue')
buf = io.BytesIO()
img.save(buf, format='PNG')
img_bytes = buf.getvalue()

print("Loading BLIP2...")
model, processor = _load_blip2()
print("BLIP2 loaded.")

# Let's test standard captioning (no question)
inputs = processor(images=img, return_tensors='pt')
with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=50)
caption = processor.decode(generated_ids[0], skip_special_tokens=True).strip()
print("Standard Caption output:", repr(caption))

# Let's test VQA with a question
question = "What color is the image?"
prompt = f"Question: {question} Answer:"
inputs = processor(images=img, text=prompt, return_tensors='pt')
with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=50)
vqa_output = processor.decode(generated_ids[0], skip_special_tokens=True).strip()
print("VQA output:", repr(vqa_output))
