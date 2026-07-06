import requests

url = "https://ed58c29d5cbb33.lhr.life"
print("Testing:", url)
for endpoint in ["/status", "/health"]:
    try:
        r = requests.get(f"{url.rstrip('/')}{endpoint}", timeout=8)
        print(f"Endpoint {endpoint} status code:", r.status_code)
        print("Response:", r.text)
    except Exception as e:
        print(f"Endpoint {endpoint} failed: {e}")
