from fastapi import APIRouter, Depends
from ..auth import require_user
from ..db import get_db
router = APIRouter()

@router.get("/me")
def me(user=Depends(require_user)):
    with get_db() as db:
        u = db.execute("SELECT * FROM users WHERE id=?", (user["user_id"],)).fetchone()
        v = db.execute("SELECT * FROM vendors WHERE user_id=?", (user["user_id"],)).fetchone()
        sub = None
        if v:
            sub = db.execute(
                """SELECT vs.status, vs.renews_at, p.*
                   FROM vendor_subscriptions vs JOIN plans p ON p.id=vs.plan_id
                   WHERE vs.vendor_id=?""",
                (v["id"],),
            ).fetchone()
        return {"id": u["id"], "role": u["role"], "is_vendor": v is not None, "vendor_id": v["id"] if v else None, "plan": dict(sub) if sub else None}
