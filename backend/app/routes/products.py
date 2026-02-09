from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..db import get_db
from ..auth import require_vendor

router = APIRouter()

class ProductCreateIn(BaseModel):
    type: str
    name: str
    short_description: str
    long_description: str
    category_slug: Optional[str] = None
    price_pesewas: int
    stock_status: str = "in_stock"
    cover_image_file_id: Optional[str] = None
    image_file_ids: List[str] = Field(default_factory=list)
    digital_file_upload_id: Optional[int] = None

def _require_active_subscription(db, vendor_id: int):
    sub = db.execute("SELECT * FROM vendor_subscriptions WHERE vendor_id=?", (vendor_id,)).fetchone()
    if not sub or sub["status"] != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    plan = db.execute("SELECT * FROM plans WHERE id=?", (sub["plan_id"],)).fetchone()
    return plan

@router.get("/categories")
def categories():
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY name").fetchall()]

@router.get("/products")
def list_products(q: Optional[str]=None, type: Optional[str]=None, category: Optional[str]=None, page: int=1, page_size: int=20):
    offset = (page-1)*page_size
    where = ["p.is_active=1"]
    params = []
    if q:
        where.append("(p.name LIKE ? OR p.short_description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if type in ("physical","digital"):
        where.append("p.type=?"); params.append(type)
    if category:
        where.append("p.category_slug=?"); params.append(category)
    where_sql = " AND ".join(where)
    with get_db() as db:
        rows = db.execute(f"""SELECT p.*, v.store_name FROM products p JOIN vendors v ON v.id=p.vendor_id
                             WHERE {where_sql} ORDER BY p.created_at DESC LIMIT ? OFFSET ?""", (*params, page_size, offset)).fetchall()
        total = db.execute(f"SELECT COUNT(*) AS c FROM products p WHERE {where_sql}", params).fetchone()["c"]
        items = [{"id": r["id"], "type": r["type"], "name": r["name"], "short_description": r["short_description"], "price_pesewas": r["price_pesewas"], "cover_image_file_id": r["cover_image_file_id"], "vendor": {"id": r["vendor_id"], "store_name": r["store_name"]}} for r in rows]
        return {"items": items, "page": page, "page_size": page_size, "total": total}

@router.get("/products/{product_id}")
def detail(product_id: int):
    with get_db() as db:
        p = db.execute("""SELECT p.*, v.store_name FROM products p JOIN vendors v ON v.id=p.vendor_id WHERE p.id=?""", (product_id,)).fetchone()
        if not p or not p["is_active"]:
            raise HTTPException(status_code=404, detail="Not found")
        imgs = db.execute("SELECT telegram_file_id FROM product_images WHERE product_id=? ORDER BY sort_order", (product_id,)).fetchall()
        return {"id": p["id"], "type": p["type"], "name": p["name"], "short_description": p["short_description"], "long_description": p["long_description"], "price_pesewas": p["price_pesewas"], "category_slug": p["category_slug"], "stock_status": p["stock_status"], "cover_image_file_id": p["cover_image_file_id"], "images": [i["telegram_file_id"] for i in imgs], "vendor": {"id": p["vendor_id"], "store_name": p["store_name"]}, "policy": {"physical_pay_on_delivery_only": True, "do_not_pay_vendor_outside_platform": True}}

@router.get("/vendor/products")
def vendor_products(vendor=Depends(require_vendor)):
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM products WHERE vendor_id=? ORDER BY created_at DESC", (vendor["vendor_id"],)).fetchall()]

@router.post("/vendor/products")
def create(payload: ProductCreateIn, vendor=Depends(require_vendor)):
    if payload.type not in ("physical","digital"):
        raise HTTPException(status_code=400, detail="Invalid type")
    if len(payload.image_file_ids) > 3:
        raise HTTPException(status_code=400, detail="Max 3 images")

    with get_db() as db:
        plan = _require_active_subscription(db, vendor["vendor_id"])
        used = db.execute("SELECT COUNT(*) AS c FROM products WHERE vendor_id=? AND is_active=1", (vendor["vendor_id"],)).fetchone()["c"]
        if int(used) >= int(plan["max_active_listings"]):
            raise HTTPException(status_code=409, detail="PLAN_LIMIT_REACHED")

        v = db.execute("SELECT * FROM vendors WHERE id=?", (vendor["vendor_id"],)).fetchone()
        if payload.type == "digital" and v["sell_type"] not in ("digital","both"):
            raise HTTPException(status_code=400, detail="Not allowed to sell digital")
        if payload.type == "physical" and v["sell_type"] not in ("physical","both"):
            raise HTTPException(status_code=400, detail="Not allowed to sell physical")

        digital_file_id = None
        if payload.type == "digital":
            if not payload.digital_file_upload_id:
                raise HTTPException(status_code=400, detail="Upload digital file via bot first")
            up = db.execute("SELECT * FROM vendor_uploads WHERE id=? AND vendor_id=? AND kind='digital' AND used_in_product_id IS NULL", (payload.digital_file_upload_id, vendor["vendor_id"])).fetchone()
            if not up:
                raise HTTPException(status_code=400, detail="Invalid upload id")
            digital_file_id = up["telegram_file_id"]

        db.execute("""INSERT INTO products(vendor_id,type,name,short_description,long_description,category_slug,price_pesewas,stock_status,cover_image_file_id)
                      VALUES(?,?,?,?,?,?,?,?,?)""", (vendor["vendor_id"], payload.type, payload.name, payload.short_description, payload.long_description, payload.category_slug, payload.price_pesewas, payload.stock_status if payload.type=="physical" else "in_stock", payload.cover_image_file_id))
        pid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

        for idx, fid in enumerate(payload.image_file_ids, start=1):
            db.execute("INSERT INTO product_images(product_id, telegram_file_id, sort_order) VALUES(?,?,?)", (pid, fid, idx))

        if payload.type == "digital":
            db.execute("INSERT INTO product_digital_assets(product_id, telegram_file_id) VALUES(?,?)", (pid, digital_file_id))
            db.execute("UPDATE vendor_uploads SET used_in_product_id=? WHERE id=?", (pid, payload.digital_file_upload_id))

        return {"id": pid}
