from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

status_obj = api.kernels_status("nikhilkumarwui/astrogen-gpu-launcher")
print("Status object:", status_obj)
print("Type:", type(status_obj))
print("Status attribute:", getattr(status_obj, "status", "N/A"))
