import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.integrations.razorpay.webhooks import parse_payload, process_webhook, verify_signature

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str | bool]:
    settings = get_settings()
    if not settings.razorpay_webhook_secret.get_secret_value():
        raise HTTPException(status_code=503, detail="Razorpay webhook processing is not configured")
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    if not verify_signature(raw_body, signature, settings):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    event_id = request.headers.get("x-razorpay-event-id", "")
    if not event_id: raise HTTPException(status_code=400, detail="Missing Razorpay event ID")
    try: payload = parse_payload(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc: raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc
    duplicate, status = process_webhook(db, event_id, payload)
    return {"received": True, "duplicate": duplicate, "status": status}
