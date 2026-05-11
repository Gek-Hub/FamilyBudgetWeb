import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

def _get_fernet():
    digest = hashlib.sha256(settings.EMAIL_ENCRYPTION_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))

def encrypt_text(value: str) -> str:
    if not value:
        return ""
    if value.startswith("enc:"):
        return value
    return "enc:" + _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_text(value: str) -> str:
    if not value:
        return ""
    if not value.startswith("enc:"):
        return value
    try:
        return _get_fernet().decrypt(value.replace("enc:", "", 1).encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value
