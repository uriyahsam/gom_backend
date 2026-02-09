from fastapi import APIRouter
from ..db import get_db
router = APIRouter()

@router.get("/plans")
def list_plans():
    with get_db() as db:
        rows = db.execute("SELECT * FROM plans ORDER BY id").fetchall()
        return [dict(r) for r in rows]
