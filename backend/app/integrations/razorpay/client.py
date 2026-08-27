from typing import Any

import httpx

from app.config import Settings, get_settings
from app.integrations.razorpay.exceptions import RazorpayAPIError, RazorpayAuthenticationError, RazorpayNotConfiguredError, RazorpayUnavailableError


class RazorpayClient:
    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.key_id = self.settings.razorpay_key_id
        self.key_secret = self.settings.razorpay_key_secret.get_secret_value()
        if not self.key_id or not self.key_secret:
            raise RazorpayNotConfiguredError("Razorpay credentials are not configured")
        self._client = httpx.Client(base_url=self.settings.razorpay_api_url, auth=(self.key_id, self.key_secret), timeout=httpx.Timeout(10.0, connect=5.0), transport=transport)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try: response = self._client.get(path, params=params)
        except httpx.RequestError as exc: raise RazorpayUnavailableError("Razorpay API is unreachable") from exc
        if response.status_code in {401, 403}: raise RazorpayAuthenticationError("Razorpay authentication failed")
        if response.status_code >= 400: raise RazorpayAPIError(f"Razorpay API request failed with status {response.status_code}")
        try: return response.json()
        except ValueError as exc: raise RazorpayAPIError("Razorpay API returned an invalid response") from exc

    @staticmethod
    def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def list_orders(self, count: int = 25) -> list[dict[str, Any]]: return self._items(self._get("/orders", {"count": min(max(count, 1), 100)}))
    def get_order(self, order_id: str) -> dict[str, Any]: return self._get(f"/orders/{order_id}")
    def list_payments(self, count: int = 25) -> list[dict[str, Any]]: return self._items(self._get("/payments", {"count": min(max(count, 1), 100)}))
    def get_payment(self, payment_id: str) -> dict[str, Any]: return self._get(f"/payments/{payment_id}")
    def list_order_payments(self, order_id: str) -> list[dict[str, Any]]: return self._items(self._get(f"/orders/{order_id}/payments"))
    def list_refunds(self, count: int = 25) -> list[dict[str, Any]]: return self._items(self._get("/refunds", {"count": min(max(count, 1), 100)}))
    def get_refund(self, refund_id: str) -> dict[str, Any]: return self._get(f"/refunds/{refund_id}")
    def list_settlements(self, count: int = 25) -> list[dict[str, Any]]: return self._items(self._get("/settlements", {"count": min(max(count, 1), 100)}))
