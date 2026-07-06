import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

notebook_path = r"C:\Users\harsh\Desktop\NTCC - In House\4_Blip_2_Caption\Final 1\4-blip-2-caption (8).ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find cells defining Dataset or data loading
for idx, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "dataset" in source.lower() and "def __getitem__" in source.lower():
            print(f"=== Cell {idx} ===")
            print(source)
            print("-" * 40)
