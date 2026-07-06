from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

owner_slug = "nikhilkumarwui/astrogen-gpu-launcher"
try:
    print("Calling api.kernels_logs...")
    logs = api.kernels_logs(owner_slug)
    print("Logs retrieved successfully!")
    print("Type of logs:", type(logs))
    # Write logs to file
    with open("kernel_console.log", "w", encoding="utf-8") as f:
        # Check if logs is a list or has stream data
        if isinstance(logs, list):
            for entry in logs:
                f.write(str(entry) + "\n")
        else:
            f.write(str(logs))
    print("Logs written to kernel_console.log")
except Exception as e:
    print("Error:", e)
