import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

notebook_path = r"C:\Users\harsh\Desktop\NTCC - In House\4_Blip_2_Caption\Final 1\4-blip-2-caption (8).ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell = nb["cells"][15]
source = "".join(cell["source"])
print(source)
