import json
import sys

# Reconfigure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

notebook_path = r"C:\Users\harsh\Desktop\NTCC - In House\4_Blip_2_Caption\Final 1\4-blip-2-caption (8).ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find code cells and print cells that contain "prompt" or "generate" or "training_args"
for idx, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if any(w in source.lower() for w in ["prompt", "generate", "tokenizer", "peft", "opt"]):
            print(f"=== Cell {idx} ===")
            print(source[:800])
            print("-" * 40)
