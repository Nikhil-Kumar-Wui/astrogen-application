from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

print("Listing kernels...")
kernels = api.kernels_list(user="nikhilkumarwui")
for k in kernels:
    print(vars(k))
