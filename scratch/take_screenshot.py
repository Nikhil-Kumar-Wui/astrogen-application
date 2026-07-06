from PIL import ImageGrab
import os

print("Taking screenshot...")
screenshot = ImageGrab.grab()
dest_path = r"c:\Users\harsh\Desktop\NTCC - In House\APPLICATION\APP 5\PROJECT1\screenshot.png"
screenshot.save(dest_path)
print(f"Screenshot saved to: {dest_path}")
