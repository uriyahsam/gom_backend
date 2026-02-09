from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import require_user
from ..db import get_db
router = APIRouter()

class AddIn(BaseModel):
    product_id: int

@router.get("/wishlist")
def get(user=Depends(require_user)):
    with get_db() as db:
        rows = db.execute("SELECT p.* FROM wishlists w JOIN products p ON p.id=w.product_id WHERE w.user_id=? ORDER BY w.created_at DESC", (user["user_id"],)).fetchall()
        return [dict(r) for r in rows]

@router.post("/wishlist")
def add(payload: AddIn, user=Depends(require_user)):
    with get_db() as db:
        if not db.execute("SELECT 1 FROM products WHERE id=? AND is_active=1", (payload.product_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Not found")
        db.execute("INSERT OR IGNORE INTO wishlists(user_id, product_id) VALUES(?,?)", (user["user_id"], payload.product_id))
        return {"ok": True}

@router.delete("/wishlist/{product_id}")
def remove(product_id: int, user=Depends(require_user)):
    with get_db() as db:
        db.execute("DELETE FROM wishlists WHERE user_id=? AND product_id=?", (user["user_id"], product_id))
        return {"ok": True}
