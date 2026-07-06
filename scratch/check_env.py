import os
from dotenv import load_dotenv

env_path = r"c:\Users\harsh\Desktop\NTCC - In House\APPLICATION\APP 5\PROJECT\.env"
print("File exists:", os.path.exists(env_path))
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        print("File content:")
        print(f.read())

load_dotenv(env_path)
print("AZURE_API_URL in os.environ:", os.environ.get("AZURE_API_URL"))
