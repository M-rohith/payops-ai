import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.razorpay.mapper import map_order, map_payment, map_refund
from app.integrations.razorpay.sync import get_or_create_integration_merchant, upsert_order, upsert_payment, upsert_refund
from app.models import WebhookEvent

logger = logging.getLogger(__name__)
SUPPORTED_EVENTS = {"payment.authorized", "payment.captured", "payment.failed", "order.paid", "refund.created", "refund.processed"}


def verify_signature(raw_body: bytes, signature: str, settings: Settings) -> bool:
    secret = settings.razorpay_webhook_secret.get_secret_value()
    if not secret or not signature: return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_payload(raw_body: bytes) -> dict[str, Any]:
    value = json.loads(raw_body)
    if not isinstance(value, dict): raise ValueError("Webhook body must be an object")
    return value


def _entity(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    candidate = payload.get("payload", {}).get(name, {}).get("entity")
    return candidate if isinstance(candidate, dict) else None


def process_webhook(session: Session, event_id: str, payload: dict[str, Any]) -> tuple[bool, str]:
    existing = session.scalar(select(WebhookEvent).where(WebhookEvent.provider == "razorpay", WebhookEvent.external_event_id == event_id))
    if existing: return True, existing.processing_status
    event_type = str(payload.get("event") or "unknown")
    event = WebhookEvent(provider="razorpay", external_event_id=event_id, event_type=event_type, received_at=datetime.now(UTC), processing_status="received")
    session.add(event); session.flush()
    merchant = get_or_create_integration_merchant(session)
    if event_type.startswith("payment.") and event_type in SUPPORTED_EVENTS:
        entity = _entity(payload, "payment")
        if entity: upsert_payment(session, merchant, map_payment(entity))
    elif event_type == "order.paid":
        entity = _entity(payload, "order")
        if entity: upsert_order(session, merchant, map_order(entity))
    elif event_type.startswith("refund.") and event_type in SUPPORTED_EVENTS:
        entity = _entity(payload, "refund")
        if entity: upsert_refund(session, merchant, map_refund(entity))
    event.processing_status = "processed" if event_type in SUPPORTED_EVENTS else "ignored"
    event.processed_at = datetime.now(UTC); session.commit()
    logger.info("Razorpay webhook handled: event_type=%s event_id=%s status=%s", event_type, event_id, event.processing_status)
    return False, event.processing_status
