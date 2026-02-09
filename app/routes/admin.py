from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import require_admin
from ..db import get_db
from ..telegram_api import send_message

router = APIRouter()

class MarkPaidIn(BaseModel):
    paid_reference: str

@router.get("/metrics")
def metrics(admin=Depends(require_admin)):
    with get_db() as db:
        vendors = db.execute("SELECT COUNT(*) AS c FROM vendors").fetchone()["c"]
        commission = db.execute("SELECT COALESCE(SUM(commission_pesewas),0) AS s FROM order_items").fetchone()["s"]
        pending = db.execute("SELECT COUNT(*) AS c FROM withdrawal_requests WHERE status='pending'").fetchone()["c"]
        return {"vendors": int(vendors), "commission_pesewas": int(commission), "withdrawals_pending": int(pending)}

@router.get("/withdrawals")
def withdrawals(status: str="pending", admin=Depends(require_admin)):
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM withdrawal_requests WHERE status=? ORDER BY requested_at ASC", (status,)).fetchall()]

@router.patch("/withdrawals/{withdrawal_id}/approve")
def approve(withdrawal_id: int, admin=Depends(require_admin)):
    with get_db() as db:
        w = db.execute("SELECT * FROM withdrawal_requests WHERE id=?", (withdrawal_id,)).fetchone()
        if not w: raise HTTPException(status_code=404, detail="Not found")
        if w["status"]!="pending": raise HTTPException(status_code=400, detail="Not pending")
        db.execute("UPDATE withdrawal_requests SET status='approved', decision_at=datetime('now'), decided_by_user_id=? WHERE id=?", (admin["user_id"], withdrawal_id))
        return {"ok": True}

@router.patch("/withdrawals/{withdrawal_id}/mark-paid")
def mark_paid(withdrawal_id: int, payload: MarkPaidIn, admin=Depends(require_admin)):
    with get_db() as db:
        wrow = db.execute("SELECT * FROM withdrawal_requests WHERE id=?", (withdrawal_id,)).fetchone()
        if not wrow: raise HTTPException(status_code=404, detail="Not found")
        if wrow["status"]!="approved": raise HTTPException(status_code=400, detail="Must be approved first")
        db.execute("INSERT INTO wallet_ledger(vendor_id,type,reason,amount_pesewas,withdrawal_id) VALUES(?, 'debit','withdrawal',?,?)", (wrow["vendor_id"], wrow["amount_pesewas"], withdrawal_id))
        db.execute("UPDATE withdrawal_requests SET status='paid', paid_reference=?, paid_at=datetime('now') WHERE id=?", (payload.paid_reference, withdrawal_id))
        vendor_user = db.execute("SELECT u.telegram_id FROM vendors v JOIN users u ON u.id=v.user_id WHERE v.id=?", (wrow["vendor_id"],)).fetchone()
        if vendor_user:
            send_message(vendor_user["telegram_id"], f"✅ Withdrawal paid: GHS {wrow['amount_pesewas']/100:.2f}\nRef: {payload.paid_reference}")
        return {"ok": True}
