import builtins
import sys

# Save the original open
original_open = builtins.open

# Define a patched open that defaults to utf-8 encoding for text files
def patched_open(*args, **kwargs):
    if len(args) > 1 and 'w' in args[1] and 'b' not in args[1]:
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
    elif 'mode' in kwargs and 'w' in kwargs['mode'] and 'b' not in kwargs['mode']:
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
    return original_open(*args, **kwargs)

# Apply the patch
builtins.open = patched_open

from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    api = KaggleApi()
    api.authenticate()
    
    owner_slug = "nikhilkumarwui/astrogen-gpu-launcher"
    
    try:
        print("Calling api.kernels_output...")
        api.kernels_output(owner_slug, ".")
        print("Successfully downloaded outputs!")
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
