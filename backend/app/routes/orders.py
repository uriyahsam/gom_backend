from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_user
from ..db import get_db
router = APIRouter()

@router.get("/orders")
def list_orders(user=Depends(require_user)):
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (user["user_id"],)).fetchall()]

@router.get("/orders/{order_id}")
def detail(order_id: int, user=Depends(require_user)):
    with get_db() as db:
        o = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, user["user_id"])).fetchone()
        if not o:
            raise HTTPException(status_code=404, detail="Not found")
        items = db.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
        d = db.execute("SELECT * FROM order_delivery_details WHERE order_id=?", (order_id,)).fetchone()
        return {"order": dict(o), "items": [dict(i) for i in items], "delivery": dict(d) if d else None}
