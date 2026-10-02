import hashlib
import os
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
    return f"{salt}${pw_hash.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        if not hashed or "$" not in hashed:
            return False
        salt, expected_hash = hashed.split("$", 1)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
        return secrets.compare_digest(actual_hash.hex(), expected_hash)
    except Exception:
        return False
