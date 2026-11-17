import os, time, hmac, hashlib, base64, json

SECRET = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_BEFORE_PUBLIC_LAUNCH")

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return base64.b64encode(salt + digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.b64decode(stored.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def make_session(user_id: int) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(
        {"uid": user_id, "exp": int(time.time()) + 604800}
    ).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + sig

def read_session(token):
    if not token or "." not in token: return None
    try:
        payload, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time(): return None
        return int(data["uid"])
    except Exception:
        return None
