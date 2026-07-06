import os
from cryptography.fernet import Fernet

# A static, strong key to obfuscate/encrypt local database and environment assets
# Compiled into bytecode, this prevents simple inspection of SQLite database or credential files.
_OBFUSCATION_KEY = b'YXN0cm9nZW5fb2JmdXNjYXRpb25fa2V5XzMyYnl0ZXM='
cipher = Fernet(_OBFUSCATION_KEY)

def encrypt_file(plain_path, enc_path):
    """Encrypt a file from plain_path and write it to enc_path, then remove plain_path."""
    if not os.path.exists(plain_path):
        return False
    try:
        with open(plain_path, 'rb') as f:
            data = f.read()
        encrypted_data = cipher.encrypt(data)
        with open(enc_path, 'wb') as f:
            f.write(encrypted_data)
        # Securely wipe the plain file
        if os.path.exists(plain_path):
            os.remove(plain_path)
        return True
    except Exception as e:
        print(f"[Security] Failed to encrypt file: {e}")
        return False

def decrypt_file(enc_path, plain_path):
    """Decrypt a file from enc_path and write it to plain_path."""
    if not os.path.exists(enc_path):
        return False
    try:
        with open(enc_path, 'rb') as f:
            encrypted_data = f.read()
        data = cipher.decrypt(encrypted_data)
        with open(plain_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"[Security] Failed to decrypt file: {e}")
        return False
