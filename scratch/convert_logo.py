import os
import sys
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
svg_path = os.path.join(PROJECT_ROOT, "frontend", "logo.svg")
png_path = os.path.join(PROJECT_ROOT, "frontend", "logo.png")
ico_path = os.path.join(PROJECT_ROOT, "frontend", "logo.ico")

print(f"SVG Path: {svg_path}")
print(f"ICO Path: {ico_path}")

try:
    # 1. Render SVG to 256x256 transparent PNG using PyQt6
    print("Rendering SVG with PyQt6...")
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        raise Exception("Invalid SVG logo file.")
        
    img = QImage(256, 256, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    
    img.save(png_path)
    print("PNG rendered successfully.")
    
    # 2. Package PNG to ICO using Pillow with multiple resolutions
    print("Converting PNG to ICO with Pillow...")
    pillow_img = Image.open(png_path)
    pillow_img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ICO generated successfully.")
    
    # Cleanup temp png
    if os.path.exists(png_path):
        os.remove(png_path)
        
    print("Done!")
except Exception as e:
    print(f"Error converting icon: {e}")
    sys.exit(1)
