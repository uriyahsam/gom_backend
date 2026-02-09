from fastapi import APIRouter
from pydantic import BaseModel
from ..auth import verify_telegram_webapp_init_data, create_jwt
from ..settings import settings
from ..db import get_db

router = APIRouter()

class AuthTelegramIn(BaseModel):
    initData: str

@router.post("/telegram")
def auth_telegram(payload: AuthTelegramIn):
    tg = verify_telegram_webapp_init_data(payload.initData, settings.BOT_TOKEN)
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE telegram_id=?", (tg["telegram_id"],)).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO users(telegram_id, first_name, username, role) VALUES(?,?,?,?)",
                (tg["telegram_id"], tg.get("first_name"), tg.get("username"), "customer"),
            )
            row = db.execute("SELECT * FROM users WHERE telegram_id=?", (tg["telegram_id"],)).fetchone()

        admin = db.execute("SELECT telegram_id FROM admins WHERE telegram_id=?", (tg["telegram_id"],)).fetchone()
        if admin and row["role"] != "admin":
            db.execute("UPDATE users SET role='admin' WHERE id=?", (row["id"],))
            row = db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()

        token = create_jwt(row["id"], row["role"])
        vendor = db.execute("SELECT id FROM vendors WHERE user_id=?", (row["id"],)).fetchone()

        return {"token": token, "user": {"id": row["id"], "role": row["role"], "is_vendor": vendor is not None}}
