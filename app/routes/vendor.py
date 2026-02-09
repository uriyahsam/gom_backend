from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from ..auth import require_user, require_vendor
from ..db import get_db
from ..paystack import init_transaction

router = APIRouter()

class VendorRegisterIn(BaseModel):
    store_name: str
    sell_type: str  # physical|digital|both
    phone: str | None = None
    email: str | None = None
    location: str | None = None

class PayoutSettingsIn(BaseModel):
    method: str  # momo|bank
    momo: dict | None = None
    bank: dict | None = None

class SubscribeInitIn(BaseModel):
    plan_id: int
    billing: str = "monthly"

class WithdrawalCreateIn(BaseModel):
    amount_pesewas: int

def _require_active_subscription(db, vendor_id: int):
    sub = db.execute("SELECT * FROM vendor_subscriptions WHERE vendor_id=?", (vendor_id,)).fetchone()
    if not sub or sub["status"] != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    plan = db.execute("SELECT * FROM plans WHERE id=?", (sub["plan_id"],)).fetchone()
    return sub, plan

@router.post("/register")
def register_vendor(payload: VendorRegisterIn, user=Depends(require_user)):
    if payload.sell_type not in ("physical","digital","both"):
        raise HTTPException(status_code=400, detail="Invalid sell_type")
    with get_db() as db:
        if db.execute("SELECT 1 FROM vendors WHERE user_id=?", (user["user_id"],)).fetchone():
            raise HTTPException(status_code=409, detail="Already a vendor")
        db.execute(
            "INSERT INTO vendors(user_id, store_name, sell_type, phone, email, location) VALUES(?,?,?,?,?,?)",
            (user["user_id"], payload.store_name, payload.sell_type, payload.phone, payload.email, payload.location),
        )
        if db.execute("SELECT role FROM users WHERE id=?", (user["user_id"],)).fetchone()["role"] == "customer":
            db.execute("UPDATE users SET role='vendor' WHERE id=?", (user["user_id"],))
        vid = db.execute("SELECT id FROM vendors WHERE user_id=?", (user["user_id"],)).fetchone()["id"]
        return {"vendor_id": vid}

@router.put("/payout-settings")
def payout(payload: PayoutSettingsIn, vendor=Depends(require_vendor)):
    if payload.method not in ("momo","bank"):
        raise HTTPException(status_code=400, detail="Invalid method")
    with get_db() as db:
        if payload.method == "momo":
            m = payload.momo or {}
            db.execute(
                """INSERT INTO vendor_payout_settings(vendor_id, method, momo_network, momo_number, account_name)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(vendor_id) DO UPDATE SET
                     method=excluded.method,
                     momo_network=excluded.momo_network,
                     momo_number=excluded.momo_number,
                     bank_name=NULL,
                     bank_account_number=NULL,
                     account_name=excluded.account_name,
                     updated_at=datetime('now')""",
                (vendor["vendor_id"], "momo", m.get("network"), m.get("number"), m.get("account_name")),
            )
        else:
            b = payload.bank or {}
            db.execute(
                """INSERT INTO vendor_payout_settings(vendor_id, method, bank_name, bank_account_number, account_name)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(vendor_id) DO UPDATE SET
                     method=excluded.method,
                     momo_network=NULL,
                     momo_number=NULL,
                     bank_name=excluded.bank_name,
                     bank_account_number=excluded.bank_account_number,
                     account_name=excluded.account_name,
                     updated_at=datetime('now')""",
                (vendor["vendor_id"], "bank", b.get("bank_name"), b.get("account_number"), b.get("account_name")),
            )
    return {"ok": True}

@router.get("/uploads")
def uploads(kind: str | None = None, vendor=Depends(require_vendor)):
    with get_db() as db:
        if kind in ("image","digital"):
            rows = db.execute("SELECT * FROM vendor_uploads WHERE vendor_id=? AND kind=? AND used_in_product_id IS NULL ORDER BY created_at DESC", (vendor["vendor_id"], kind)).fetchall()
        else:
            rows = db.execute("SELECT * FROM vendor_uploads WHERE vendor_id=? AND used_in_product_id IS NULL ORDER BY created_at DESC", (vendor["vendor_id"],)).fetchall()
        return [dict(r) for r in rows]

@router.post("/subscribe/init")
def subscribe_init(payload: SubscribeInitIn, vendor=Depends(require_vendor)):
    if payload.billing not in ("monthly","quarterly"):
        raise HTTPException(status_code=400, detail="Invalid billing")
    with get_db() as db:
        plan = db.execute("SELECT * FROM plans WHERE id=?", (payload.plan_id,)).fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        u = db.execute("SELECT * FROM users WHERE id=?", (vendor["user_id"],)).fetchone()
        v = db.execute("SELECT * FROM vendors WHERE id=?", (vendor["vendor_id"],)).fetchone()
        email = (v["email"] or "").strip() or f"{u['telegram_id']}@telegram.local"
        reference = f"sub_{vendor['vendor_id']}_{int(datetime.utcnow().timestamp())}"
        amount = int(plan["price_pesewas"]) * (3 if payload.billing=="quarterly" else 1)
        resp = init_transaction(email=email, amount_pesewas=amount, reference=reference, metadata={"purpose":"subscription","vendor_id":vendor["vendor_id"],"plan_id":payload.plan_id,"billing":payload.billing})
        db.execute("INSERT INTO payments(purpose, vendor_id, reference, amount_pesewas, status) VALUES('subscription',?,?,?,'initiated')", (vendor["vendor_id"], reference, amount))
        return {"reference": reference, "authorization_url": resp["data"]["authorization_url"]}

@router.get("/plan/usage")
def plan_usage(vendor=Depends(require_vendor)):
    with get_db() as db:
        sub, plan = _require_active_subscription(db, vendor["vendor_id"])
        used = db.execute("SELECT COUNT(*) AS c FROM products WHERE vendor_id=? AND is_active=1", (vendor["vendor_id"],)).fetchone()["c"]
        return {"used": int(used), "limit": int(plan["max_active_listings"]), "renews_at": sub["renews_at"]}

@router.get("/wallet")
def wallet(vendor=Depends(require_vendor)):
    with get_db() as db:
        credits = db.execute("SELECT COALESCE(SUM(amount_pesewas),0) AS s FROM wallet_ledger WHERE vendor_id=? AND type='credit'", (vendor["vendor_id"],)).fetchone()["s"]
        debits  = db.execute("SELECT COALESCE(SUM(amount_pesewas),0) AS s FROM wallet_ledger WHERE vendor_id=? AND type='debit'", (vendor["vendor_id"],)).fetchone()["s"]
        return {"available_pesewas": int(credits) - int(debits)}

@router.post("/withdrawals")
def request_withdrawal(payload: WithdrawalCreateIn, vendor=Depends(require_vendor)):
    with get_db() as db:
        credits = db.execute("SELECT COALESCE(SUM(amount_pesewas),0) AS s FROM wallet_ledger WHERE vendor_id=? AND type='credit'", (vendor["vendor_id"],)).fetchone()["s"]
        debits  = db.execute("SELECT COALESCE(SUM(amount_pesewas),0) AS s FROM wallet_ledger WHERE vendor_id=? AND type='debit'", (vendor["vendor_id"],)).fetchone()["s"]
        available = int(credits) - int(debits)
        if payload.amount_pesewas <= 0 or payload.amount_pesewas > available:
            raise HTTPException(status_code=400, detail="Invalid amount")
        db.execute("INSERT INTO withdrawal_requests(vendor_id, amount_pesewas, status) VALUES(?,?,'pending')", (vendor["vendor_id"], payload.amount_pesewas))
        wid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return {"withdrawal_id": wid, "status": "pending"}
