from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import require_user
from ..db import get_db
router = APIRouter()

class AddIn(BaseModel):
    product_id: int
    qty: int = 1

@router.get("/cart")
def get_cart(user=Depends(require_user)):
    with get_db() as db:
        cart = db.execute("SELECT id FROM carts WHERE user_id=?", (user["user_id"],)).fetchone()
        if not cart:
            db.execute("INSERT INTO carts(user_id) VALUES(?)", (user["user_id"],))
            cart = db.execute("SELECT id FROM carts WHERE user_id=?", (user["user_id"],)).fetchone()
        rows = db.execute("SELECT ci.id, ci.qty, p.id AS product_id, p.name, p.type, p.price_pesewas FROM cart_items ci JOIN products p ON p.id=ci.product_id WHERE ci.cart_id=?", (cart["id"],)).fetchall()
        return {"items": [dict(r) for r in rows]}

@router.post("/cart/items")
def add_item(payload: AddIn, user=Depends(require_user)):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail="Invalid qty")
    with get_db() as db:
        cart = db.execute("SELECT id FROM carts WHERE user_id=?", (user["user_id"],)).fetchone()
        if not cart:
            db.execute("INSERT INTO carts(user_id) VALUES(?)", (user["user_id"],))
            cart = db.execute("SELECT id FROM carts WHERE user_id=?", (user["user_id"],)).fetchone()
        if not db.execute("SELECT 1 FROM products WHERE id=? AND is_active=1", (payload.product_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Product not found")
        db.execute("INSERT INTO cart_items(cart_id, product_id, qty) VALUES(?,?,?)", (cart["id"], payload.product_id, payload.qty))
        return {"ok": True}

@router.delete("/cart/items/{item_id}")
def remove(item_id: int, user=Depends(require_user)):
    with get_db() as db:
        db.execute("DELETE FROM cart_items WHERE id=? AND cart_id=(SELECT id FROM carts WHERE user_id=?)", (item_id, user["user_id"]))
        return {"ok": True}
