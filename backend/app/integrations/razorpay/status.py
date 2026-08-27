from app.config import Settings, get_settings
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.exceptions import RazorpayError, RazorpayNotConfiguredError
from app.integrations.razorpay.schemas import ConnectionStatus


def connection_status(settings: Settings | None = None, client: RazorpayClient | None = None) -> ConnectionStatus:
    config = settings or get_settings(); configured = bool(config.razorpay_key_id and config.razorpay_key_secret.get_secret_value())
    mode = "test" if config.razorpay_key_id.startswith("rzp_test_") else ("live" if config.razorpay_key_id.startswith("rzp_live_") else "unknown")
    if not configured: return ConnectionStatus(configured=False, reachable=False, mode=mode, detail="Credentials are not configured")
    if mode != "test": return ConnectionStatus(configured=True, reachable=False, mode=mode, detail="Only Razorpay Test Mode is allowed")
    try:
        active_client = client or RazorpayClient(config); items = active_client.list_payments(1)
        return ConnectionStatus(configured=True, reachable=True, mode="test", entities_returned=len(items))
    except RazorpayNotConfiguredError: return ConnectionStatus(configured=False, reachable=False, mode=mode, detail="Credentials are not configured")
    except RazorpayError as exc: return ConnectionStatus(configured=True, reachable=False, mode=mode, detail=str(exc))
