"""Receipt HTML endpoint (Phase 30, Step 7 — Wave 0 part A)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


router = APIRouter(prefix="/bookings", tags=["receipts"])

_RECEIPT_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Receipt {booking_id}</title>
<style>
body{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;max-width:720px;margin:40px auto;padding:0 20px;color:#111;}
.hdr{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #0f3d5c;padding-bottom:16px;margin-bottom:24px;}
.brand{font-size:22px;font-weight:800;color:#0f3d5c;}
.brand small{display:block;font-weight:400;font-size:11px;color:#6b7280;letter-spacing:.08em;text-transform:uppercase;margin-top:2px;}
.doc{font-size:12px;color:#6b7280;text-align:right;}
h1{font-size:18px;margin:0 0 16px;color:#0f3d5c;}
table{width:100%;border-collapse:collapse;margin:16px 0;}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:13.5px;}
th{color:#6b7280;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.05em;}
.total-row td{font-weight:700;font-size:15px;color:#0f3d5c;border-bottom:none;padding-top:16px;}
.note{font-size:11.5px;color:#6b7280;margin-top:24px;line-height:1.6;}
.btn{display:inline-block;margin-top:24px;padding:10px 20px;background:#0f3d5c;color:#fff;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;border:none;cursor:pointer;}
@media print{.btn{display:none;} body{margin:0;}}
</style></head><body>
<div class="hdr">
  <div class="brand">Platform-X<small>Booking receipt</small></div>
  <div class="doc">Booking ID: {booking_id}<br>Date: {created_at}<br>Status: <strong>{status}</strong></div>
</div>
<h1>{tenant_name}</h1>
<p style="font-size:13.5px;color:#374151;margin:0 0 4px;">{location}</p>
<p style="font-size:13.5px;color:#374151;margin:0;">{customer_email}</p>
<table><thead><tr><th>Item</th><th>Details</th><th>Amount</th></tr></thead><tbody>
<tr><td>{service_name}</td><td>{check_in} to {check_out} | {guests} guests</td><td>{total_amount} {currency}</td></tr>
<tr class="total-row"><td colspan="2">Total</td><td>{total_amount} {currency}</td></tr>
</tbody></table>
<p class="note">System-generated receipt from Platform-X on behalf of {tenant_name}. Payment status: <strong>{payment_status}</strong>.<br>Generated: {generated_at}</p>
<button class="btn" onclick="window.print()">Print / Save as PDF</button>
</body></html>"""


@router.get("/{booking_id}/receipt", response_class=HTMLResponse)
def booking_receipt(
    request: Request,
    booking_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == user.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    t = db.query(Tenant).filter(Tenant.id == b.tenant_id).one_or_none()
    cfg = (t.config or {}) if t else {}
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = _RECEIPT_HTML.format(
        booking_id=b.id,
        created_at=b.created_at.strftime("%Y-%m-%d") if b.created_at else now,
        status=b.status,
        tenant_name=(t.name if t else "Business"),
        location=(cfg.get("location") or ""),
        customer_email=user.email,
        service_name=b.service_name,
        check_in=str(b.check_in),
        check_out=(str(b.check_out) if b.check_out else "-"),
        guests=b.guests,
        total_amount=str(b.total_amount),
        currency=b.currency,
        payment_status=b.payment_status,
        generated_at=now,
    )
    return HTMLResponse(content=html)
