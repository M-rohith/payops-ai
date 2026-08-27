from datetime import UTC, datetime
from typing import Any

from app.integrations.razorpay.schemas import MappedOrder, MappedPayment, MappedRefund, MappedSettlement


def _timestamp(value: Any) -> datetime:
    try: return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError): return datetime.now(UTC)


def map_order(payload: dict[str, Any]) -> MappedOrder:
    status = str(payload.get("status") or "created")
    return MappedOrder(external_order_id=str(payload["id"]), amount=int(payload.get("amount") or 0), currency=str(payload.get("currency") or "INR"), status="paid" if status == "paid" else (status if status in {"created", "failed", "cancelled"} else "created"), created_at=_timestamp(payload.get("created_at")))


def map_payment(payload: dict[str, Any]) -> MappedPayment:
    status = str(payload.get("status") or "authorized")
    if status not in {"authorized", "captured", "failed", "refunded"}: status = "authorized"
    return MappedPayment(external_payment_id=str(payload["id"]), external_order_id=str(payload["order_id"]) if payload.get("order_id") else None, amount=int(payload.get("amount") or 0), currency=str(payload.get("currency") or "INR"), method=str(payload.get("method") or "unknown"), status=status, error_code=str(payload["error_code"]) if payload.get("error_code") else None, error_description=str(payload["error_description"]) if payload.get("error_description") else None, captured=bool(payload.get("captured")) or status in {"captured", "refunded"}, created_at=_timestamp(payload.get("created_at")))


def map_refund(payload: dict[str, Any]) -> MappedRefund:
    return MappedRefund(external_refund_id=str(payload["id"]), external_payment_id=str(payload["payment_id"]), amount=int(payload.get("amount") or 0), status=str(payload.get("status") or "created"), created_at=_timestamp(payload.get("created_at")))


def map_settlement(payload: dict[str, Any]) -> MappedSettlement:
    created = _timestamp(payload.get("created_at"))
    status = str(payload.get("status") or "pending")
    return MappedSettlement(external_settlement_id=str(payload["id"]), amount=int(payload.get("amount") or 0), fees=int(payload.get("fees") or 0) + int(payload.get("tax") or 0), status="processed" if status == "processed" else "pending", settled_at=created if status == "processed" else None, created_at=created)
