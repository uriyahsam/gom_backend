import requests, hmac, hashlib
from .settings import settings

PAYSTACK_BASE = "https://api.paystack.co"

def init_transaction(email: str, amount_pesewas: int, reference: str, callback_url: str | None = None, metadata: dict | None = None):
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {"email": email, "amount": amount_pesewas, "reference": reference}
    if callback_url:
        payload["callback_url"] = callback_url
    if metadata:
        payload["metadata"] = metadata
    r = requests.post(f"{PAYSTACK_BASE}/transaction/initialize", json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def verify_signature(raw_body: bytes, signature: str) -> bool:
    computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)
