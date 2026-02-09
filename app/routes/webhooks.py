from fastapi import APIRouter, Request, HTTPException
import json
from datetime import datetime, timedelta
from ..paystack import verify_signature
from ..db import get_db
from ..telegram_api import send_message, send_document

router = APIRouter()

@router.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("x-paystack-signature", "")
    if not verify_signature(raw, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(raw.decode("utf-8"))
    if event.get("event") != "charge.success":
        return {"ok": True}
    data = event.get("data", {})
    ref = data.get("reference")
    if not ref:
        return {"ok": True}

    with get_db() as db:
        pay = db.execute("SELECT * FROM payments WHERE reference=?", (ref,)).fetchone()
        if not pay:
            return {"ok": True}
        if pay["status"] == "success":
            return {"ok": True}
        db.execute("UPDATE payments SET status='success', raw_event_json=? WHERE reference=?", (json.dumps(event), ref))

        if pay["purpose"] == "order" and pay["order_id"]:
            oid = pay["order_id"]
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            items = db.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
            for it in items:
                if it["product_type"] != "digital":
                    continue
                db.execute("INSERT INTO wallet_ledger(vendor_id,type,reason,amount_pesewas,order_id) VALUES(?, 'credit','sale',?,?)", (it["vendor_id"], it["vendor_net_pesewas"], oid))

            order = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            user = db.execute("SELECT telegram_id FROM users WHERE id=?", (order["user_id"],)).fetchone()
            if user:
                send_message(user["telegram_id"], "✅ Payment successful! Delivering your digital items now…")
                for it in items:
                    if it["product_type"] != "digital":
                        continue
                    asset = db.execute("SELECT telegram_file_id FROM product_digital_assets WHERE product_id=?", (it["product_id"],)).fetchone()
                    if asset:
                        send_document(user["telegram_id"], asset["telegram_file_id"], caption=it["name_snapshot"])
            return {"ok": True}

        if pay["purpose"] == "subscription" and pay["vendor_id"]:
            meta = (data.get("metadata") or {})
            plan_id = int(meta.get("plan_id") or 2)
            billing = meta.get("billing") or "monthly"
            renews_at = (datetime.utcnow() + timedelta(days=30 if billing=="monthly" else 90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            db.execute(
                """INSERT INTO vendor_subscriptions(vendor_id, plan_id, status, started_at, renews_at, paystack_reference)
                   VALUES(?, ?, 'active', datetime('now'), ?, ?)
                   ON CONFLICT(vendor_id) DO UPDATE SET plan_id=excluded.plan_id, status='active', renews_at=excluded.renews_at, paystack_reference=excluded.paystack_reference""",
                (pay["vendor_id"], plan_id, renews_at, ref),
            )
            vendor_user = db.execute("SELECT u.telegram_id FROM vendors v JOIN users u ON u.id=v.user_id WHERE v.id=?", (pay["vendor_id"],)).fetchone()
            if vendor_user:
                send_message(vendor_user["telegram_id"], f"✅ Subscription active. Plan ID: {plan_id}. Renews: {renews_at}")
            return {"ok": True}

    return {"ok": True}
