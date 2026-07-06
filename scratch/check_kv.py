import requests
import base64

token = "ff41f0e33004"
api_url = f"https://keyvalue.immanuel.co/api/keyval/GetValue/astrogen_studio/token_{token}"
resp = requests.get(api_url)
print("Status Code:", resp.status_code)
print("Raw value:", resp.text)
if resp.status_code == 200:
    val = resp.text.strip().strip('"')
    if val and val != "null":
        try:
            decoded = base64.b64decode(val.encode()).decode()
            print("Decoded URL:", decoded)
        except Exception as e:
            print("Decode error:", e)
