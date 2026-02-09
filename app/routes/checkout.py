from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import require_user
from ..db import get_db
from ..settings import settings
from ..paystack import init_transaction

router = APIRouter()

class DeliveryIn(BaseModel):
    full_name: str
    phone: str
    region: str
    city: str
    address: str
    notes: str | None = None

class PhysicalIn(BaseModel):
    cart_item_ids: list[int]
    delivery: DeliveryIn

class DigitalInitIn(BaseModel):
    cart_item_ids: list[int]

@router.post("/physical")
def physical(payload: PhysicalIn, user=Depends(require_user)):
    if not payload.cart_item_ids:
        raise HTTPException(status_code=400, detail="No items")
    with get_db() as db:
        q = ",".join("?"*len(payload.cart_item_ids))
        rows = db.execute(f"""SELECT ci.id, ci.qty, p.* FROM cart_items ci
                               JOIN carts c ON c.id=ci.cart_id
                               JOIN products p ON p.id=ci.product_id
                               WHERE c.user_id=? AND ci.id IN ({q})""", (user["user_id"], *payload.cart_item_ids)).fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No items")
        if any(r["type"]!="physical" for r in rows):
            raise HTTPException(status_code=400, detail="Physical checkout must contain physical items only")
        total = sum(int(r["price_pesewas"])*int(r["qty"]) for r in rows)
        db.execute("INSERT INTO orders(user_id,type,status,total_pesewas) VALUES(?, 'physical','new',?)", (user["user_id"], total))
        oid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        for r in rows:
            db.execute("""INSERT INTO order_items(order_id, product_id, vendor_id, product_type, name_snapshot, price_pesewas, qty)
                          VALUES(?,?,?,?,?,?,?)""", (oid, r["id"], r["vendor_id"], "physical", r["name"], r["price_pesewas"], r["qty"]))
            db.execute("INSERT OR REPLACE INTO vendor_order_status(order_id, vendor_id, status) VALUES(?,?, 'new')", (oid, r["vendor_id"]))
        d = payload.delivery
        db.execute("""INSERT INTO order_delivery_details(order_id, full_name, phone, region, city, address, notes)
                      VALUES(?,?,?,?,?,?,?)""", (oid, d.full_name, d.phone, d.region, d.city, d.address, d.notes))
        db.execute(f"DELETE FROM cart_items WHERE id IN ({q}) AND cart_id=(SELECT id FROM carts WHERE user_id=?)", (*payload.cart_item_ids, user["user_id"]))
        return {"order_id": oid, "payment_method": "pay_on_delivery", "warnings": ["PAY ON DELIVERY ONLY (physical items).", "Do not send money to vendors outside the platform."]}

@router.post("/digital/init")
def digital_init(payload: DigitalInitIn, user=Depends(require_user)):
    if not payload.cart_item_ids:
        raise HTTPException(status_code=400, detail="No items")
    with get_db() as db:
        q = ",".join("?"*len(payload.cart_item_ids))
        rows = db.execute(f"""SELECT ci.id, ci.qty, p.* FROM cart_items ci
                               JOIN carts c ON c.id=ci.cart_id
                               JOIN products p ON p.id=ci.product_id
                               WHERE c.user_id=? AND ci.id IN ({q})""", (user["user_id"], *payload.cart_item_ids)).fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No items")
        if any(r["type"]!="digital" for r in rows):
            raise HTTPException(status_code=400, detail="Digital checkout must contain digital items only")
        total = sum(int(r["price_pesewas"])*int(r["qty"]) for r in rows)
        db.execute("INSERT INTO orders(user_id,type,status,total_pesewas) VALUES(?, 'digital','pending_payment',?)", (user["user_id"], total))
        oid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        ref = f"ord_{oid}_{user['user_id']}"
        db.execute("UPDATE orders SET paystack_reference=? WHERE id=?", (ref, oid))
        for r in rows:
            gross = int(r["price_pesewas"])*int(r["qty"])
            commission = int(round(gross*settings.COMMISSION_RATE))
            net = gross-commission
            db.execute("""INSERT INTO order_items(order_id, product_id, vendor_id, product_type, name_snapshot, price_pesewas, qty, commission_pesewas, vendor_net_pesewas)
                      VALUES(?,?,?,?,?,?,?,?,?)""", (oid, r["id"], r["vendor_id"], "digital", r["name"], r["price_pesewas"], r["qty"], commission, net))
        u = db.execute("SELECT telegram_id FROM users WHERE id=?", (user["user_id"],)).fetchone()
        email = f"{u['telegram_id']}@telegram.local"
        resp = init_transaction(email=email, amount_pesewas=total, reference=ref, metadata={"purpose":"order","order_id":oid})
        db.execute("INSERT INTO payments(purpose, order_id, reference, amount_pesewas, status) VALUES('order',?,?,?,'initiated')", (oid, ref, total))
        db.execute(f"DELETE FROM cart_items WHERE id IN ({q}) AND cart_id=(SELECT id FROM carts WHERE user_id=?)", (*payload.cart_item_ids, user["user_id"]))
        return {"order_id": oid, "reference": ref, "authorization_url": resp["data"]["authorization_url"]}
