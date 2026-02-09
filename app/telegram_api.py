import requests
from .settings import settings

def tg_api(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}"

def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(tg_api("sendMessage"), json=payload, timeout=30)

def send_document(chat_id: int, file_id: str, caption: str = ""):
    payload = {"chat_id": chat_id, "document": file_id}
    if caption:
        payload["caption"] = caption
    requests.post(tg_api("sendDocument"), json=payload, timeout=60)
