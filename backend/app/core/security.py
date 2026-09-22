import base64
import hashlib
import hmac
import json
import time
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.app.core.config import settings

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = hashlib.sha256(settings.jwt_secret.encode()).digest()[:16]
    return "scrypt$" + base64.urlsafe_b64encode(salt).decode() + "$" + hashlib.scrypt(
        password.encode(), salt=salt, n=16384, r=8, p=1
    ).hex()


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, salt_text, expected = hashed.split("$", 2)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_access_token(subject: str, role: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": subject, "role": role, "exp": int(time.time()) + settings.access_token_expire_minutes * 60}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(settings.jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            raise ValueError
        return data
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
