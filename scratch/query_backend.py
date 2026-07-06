import requests

for endpoint in ["status", "settings", "kaggle/status"]:
    try:
        r = requests.get(f"http://127.0.0.1:8001/{endpoint}")
        print(f"=== {endpoint} ===")
        print(r.json())
    except Exception as e:
        print(f"Error calling {endpoint}: {e}")
