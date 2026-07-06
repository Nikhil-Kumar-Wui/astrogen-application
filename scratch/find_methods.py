from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

# Find any methods on api that have 'log' or 'output' in their name
methods = [m for m in dir(api) if 'log' in m.lower() or 'output' in m.lower()]
print("Matching methods:", methods)
