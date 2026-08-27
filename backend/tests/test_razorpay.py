import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.api.webhooks as webhook_api
from app.config import Settings
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.exceptions import RazorpayAuthenticationError, RazorpayNotConfiguredError
from app.integrations.razorpay.mapper import map_order, map_payment, map_refund
from app.integrations.razorpay.status import connection_status
from app.integrations.razorpay.sync import synchronize
from app.models import Merchant, Payment, Refund, WebhookEvent

NOW = 1_777_000_000


def settings(webhook_secret: str = "webhook-test-secret") -> Settings:
    return Settings(razorpay_key_id="rzp_" + "test_publicfake", razorpay_key_secret=SecretStr("privatefake"), razorpay_webhook_secret=SecretStr(webhook_secret), razorpay_api_url="https://api.razorpay.test/v1")


def mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        expected = "Basic " + base64.b64encode(("rzp_" + "test_publicfake:privatefake").encode()).decode()
        assert request.headers["authorization"] == expected
        payloads = {
            "/v1/orders": {"items": [{"id": "order_real_test_1", "amount": 12500, "currency": "INR", "status": "created", "created_at": NOW}]},
            "/v1/payments": {"items": [{"id": "pay_real_test_1", "order_id": "order_real_test_1", "amount": 12500, "currency": "INR", "method": "upi", "status": "captured", "captured": True, "created_at": NOW}]},
            "/v1/refunds": {"items": [{"id": "rfnd_real_test_1", "payment_id": "pay_real_test_1", "amount": 2500, "status": "processed", "created_at": NOW}]},
            "/v1/settlements": {"items": []},
        }
        return httpx.Response(200, json=payloads.get(request.url.path, {"items": []}))
    return httpx.MockTransport(handler)


def test_mapping_preserves_ids_optional_fields_and_minor_units() -> None:
    order = map_order({"id": "order_1", "amount": 10101, "created_at": NOW})
    payment = map_payment({"id": "pay_1", "amount": 10101, "status": "authorized", "created_at": NOW})
    refund = map_refund({"id": "rfnd_1", "payment_id": "pay_1", "amount": 501, "created_at": NOW})
    assert order.amount == payment.amount == 10101
    assert isinstance(refund.amount, int) and refund.amount == 501
    assert payment.external_order_id is None and payment.error_code is None


def test_client_auth_and_connection_status() -> None:
    client = RazorpayClient(settings(), transport=mock_transport())
    result = connection_status(settings(), client)
    assert result.configured and result.reachable and result.mode == "test" and result.entities_returned == 1
    missing = Settings(razorpay_key_id="", razorpay_key_secret=SecretStr(""))
    assert connection_status(missing).configured is False
    try: RazorpayClient(missing)
    except RazorpayNotConfiguredError: pass
    else: raise AssertionError("Missing credentials must fail closed")


def test_authentication_failure_is_sanitized() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(401, json={"error": {"description": "denied"}}))
    try: RazorpayClient(settings(), transport=transport).list_payments(1)
    except RazorpayAuthenticationError as exc:
        assert "privatefake" not in str(exc) and "publicfake" not in str(exc)
    else: raise AssertionError("Expected authentication error")


def test_sync_is_idempotent_and_source_isolated(db: Session) -> None:
    client = RazorpayClient(settings(), transport=mock_transport())
    first = synchronize(db, client, 5); second = synchronize(db, client, 5)
    assert first.orders_created == first.payments_created == first.refunds_created == 1
    assert second.orders_created == second.payments_created == second.refunds_created == 0
    assert second.orders_updated == second.payments_updated == second.refunds_updated == 1
    razorpay = db.scalar(select(Merchant).where(Merchant.source == "razorpay"))
    demo = db.scalar(select(Merchant).where(Merchant.source == "demo"))
    assert razorpay is not None and demo is not None and razorpay.id != demo.id
    assert db.scalar(select(func.count(Payment.id)).where(Payment.external_payment_id == "pay_real_test_1")) == 1


def signed_headers(raw: bytes, event_id: str, secret: str = "webhook-test-secret") -> dict[str, str]:
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return {"x-razorpay-signature": signature, "x-razorpay-event-id": event_id, "content-type": "application/json"}


def payment_event(status: str, captured: bool) -> bytes:
    return json.dumps({"event": f"payment.{status}", "payload": {"payment": {"entity": {"id": "pay_webhook_1", "order_id": "order_webhook_1", "amount": 9900, "currency": "INR", "method": "card", "status": status, "captured": captured, "created_at": NOW}}}}, separators=(",", ":")).encode()


def test_valid_raw_signature_duplicate_and_supported_mapping(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings())
    raw = payment_event("captured", True); headers = signed_headers(raw, "evt_1")
    first = client.post("/api/webhooks/razorpay", content=raw, headers=headers)
    duplicate = client.post("/api/webhooks/razorpay", content=raw, headers=headers)
    assert first.status_code == 200 and first.json()["duplicate"] is False
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True
    assert db.scalar(select(func.count(WebhookEvent.id)).where(WebhookEvent.external_event_id == "evt_1")) == 1
    payment = db.scalar(select(Payment).where(Payment.external_payment_id == "pay_webhook_1"))
    assert payment.status == "captured" and payment.amount == 9900 and isinstance(payment.amount, int)


def test_invalid_signature_and_raw_body_semantics(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings())
    raw = b'{ "event": "payment.captured", "payload": {} }'
    altered = json.dumps(json.loads(raw)).encode()
    response = client.post("/api/webhooks/razorpay", content=altered, headers=signed_headers(raw, "evt_raw"))
    assert response.status_code == 401
    assert client.post("/api/webhooks/razorpay", content=raw, headers={"x-razorpay-signature": "invalid", "x-razorpay-event-id": "evt_bad"}).status_code == 401


def test_unsupported_event_is_acknowledged(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings())
    raw = json.dumps({"event": "invoice.paid", "payload": {}}).encode()
    response = client.post("/api/webhooks/razorpay", content=raw, headers=signed_headers(raw, "evt_unsupported"))
    assert response.status_code == 200 and response.json()["status"] == "ignored"


def test_out_of_order_payment_does_not_downgrade(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings())
    captured = payment_event("captured", True); authorized = payment_event("authorized", False)
    assert client.post("/api/webhooks/razorpay", content=captured, headers=signed_headers(captured, "evt_captured")).status_code == 200
    assert client.post("/api/webhooks/razorpay", content=authorized, headers=signed_headers(authorized, "evt_authorized")).status_code == 200
    assert db.scalar(select(Payment).where(Payment.external_payment_id == "pay_webhook_1")).status == "captured"


def test_refund_event_and_absent_webhook_secret(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings())
    raw = json.dumps({"event": "refund.processed", "payload": {"refund": {"entity": {"id": "rfnd_webhook_1", "payment_id": "pay_missing_1", "amount": 700, "status": "processed", "created_at": NOW}}}}).encode()
    assert client.post("/api/webhooks/razorpay", content=raw, headers=signed_headers(raw, "evt_refund")).status_code == 200
    assert db.scalar(select(Refund).where(Refund.external_refund_id == "rfnd_webhook_1")).amount == 700
    monkeypatch.setattr(webhook_api, "get_settings", lambda: settings(""))
    assert client.post("/api/webhooks/razorpay", content=b"{}", headers={}).status_code == 503
