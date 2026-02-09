from fastapi import APIRouter, Request
from ..settings import settings
from ..db import get_db
from ..telegram_api import send_message

router = APIRouter()

def webapp_button(url: str, text: str = "🛍️ Open Market"):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": url}}]]}

@router.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    doc = msg.get("document")
    web_url = settings.BASE_WEBAPP_URL.strip() or "https://example.com"

    if text.startswith("/start"):
        send_message(chat_id,
            f"Welcome to {settings.PLATFORM_NAME}!\n\n"
            "✅ Digital products: Pay online and receive instantly.\n"
            "🚚 Physical products: PAY ON DELIVERY ONLY.\n"
            "⚠️ Never send money to vendors outside the platform for physical items.",
            reply_markup=webapp_button(web_url)
        )
        return {"ok": True}

    if text.startswith("/upload_digital"):
        send_message(chat_id, "Send the digital file now (PDF/ZIP/etc).")
        with get_db() as db:
            db.execute("INSERT OR REPLACE INTO upload_states(telegram_id, kind) VALUES(?, 'digital')", (chat_id,))
        return {"ok": True}

    if text.startswith("/upload_image"):
        send_message(chat_id, "Send the product image now (as a document).")
        with get_db() as db:
            db.execute("INSERT OR REPLACE INTO upload_states(telegram_id, kind) VALUES(?, 'image')", (chat_id,))
        return {"ok": True}

    if doc:
        file_id = doc.get("file_id")
        file_name = doc.get("file_name")
        mime_type = doc.get("mime_type")
        file_size = doc.get("file_size")
        with get_db() as db:
            u = db.execute("SELECT * FROM users WHERE telegram_id=?", (chat_id,)).fetchone()
            if not u:
                db.execute("INSERT INTO users(telegram_id, role) VALUES(?, 'customer')", (chat_id,))
                u = db.execute("SELECT * FROM users WHERE telegram_id=?", (chat_id,)).fetchone()
            v = db.execute("SELECT * FROM vendors WHERE user_id=?", (u["id"],)).fetchone()
            if not v:
                send_message(chat_id, "Register as a vendor in the Web App first (Open Market).")
                return {"ok": True}
            state = db.execute("SELECT kind FROM upload_states WHERE telegram_id=?", (chat_id,)).fetchone()
            kind = state["kind"] if state else None
            if kind not in ("digital","image"):
                send_message(chat_id, "Use /upload_digital or /upload_image first, then send the file.")
                return {"ok": True}
            db.execute("INSERT INTO vendor_uploads(vendor_id, kind, telegram_file_id, file_name, mime_type, file_size) VALUES(?,?,?,?,?,?)",
                       (v["id"], kind, file_id, file_name, mime_type, file_size))
            db.execute("DELETE FROM upload_states WHERE telegram_id=?", (chat_id,))
        send_message(chat_id, f"✅ Saved {kind} upload. You can select it in your Vendor dashboard.")
        return {"ok": True}

    if text.startswith("/help"):
        send_message(chat_id, "Commands:\n/start\n/upload_digital\n/upload_image")
        return {"ok": True}

    return {"ok": True}
