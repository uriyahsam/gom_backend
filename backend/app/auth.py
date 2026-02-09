import json, hmac, hashlib, time
from urllib.parse import parse_qsl
from typing import Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from .settings import settings
from .db import get_db

bearer = HTTPBearer(auto_error=False)

def verify_telegram_webapp_init_data(init_data: str, bot_token: str, max_age_seconds: int = 24*3600) -> Dict[str, Any]:
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not set")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    auth_date = pairs.get("auth_date")
    if auth_date:
        try:
            if int(time.time()) - int(auth_date) > max_age_seconds:
                raise HTTPException(status_code=401, detail="initData expired")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid auth_date")

    data_check_string = "\n".join([f"{k}={pairs[k]}" for k in sorted(pairs.keys())])
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    expected = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Missing user field")
    try:
        user = json.loads(user_raw)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user JSON")

    return {"telegram_id": int(user.get("id")), "first_name": user.get("first_name"), "username": user.get("username")}

def create_jwt(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "iat": int(time.time())}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        decoded = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return {"user_id": int(decoded["sub"]), "role": decoded.get("role", "customer")}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(user=Depends(require_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user

def require_vendor(user=Depends(require_user)):
    with get_db() as db:
        v = db.execute("SELECT v.id FROM vendors v WHERE v.user_id=?", (user["user_id"],)).fetchone()
        if not v:
            raise HTTPException(status_code=403, detail="Vendor required")
        return {"user_id": user["user_id"], "role": user["role"], "vendor_id": v["id"]}
