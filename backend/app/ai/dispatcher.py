import json
import logging
import time
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.exceptions import AIToolError
from app.ai.tool_schemas import TOOL_MODELS
from app.ai import tools

logger = logging.getLogger(__name__)

TOOL_FUNCTIONS: dict[str, Callable[..., dict]] = {
    "get_dashboard_summary": tools.dashboard_summary,
    "get_payment_failure_stats": tools.payment_failure_stats,
    "get_failure_reason_breakdown": tools.failure_reason_breakdown,
    "compare_failure_rates": tools.compare_failure_rates,
    "get_failed_payments": tools.failed_payments,
    "get_settlement_variance": tools.settlement_variance,
    "get_reconciliation_issues": tools.reconciliation_issues,
    "get_alerts": tools.alerts,
    "get_payment_details": tools.payment_details,
}


def dispatch_tool(session: Session, name: str, raw_arguments: str | dict, selected_source: str) -> dict:
    started = time.perf_counter()
    if name not in TOOL_FUNCTIONS or name not in TOOL_MODELS: raise AIToolError("The requested PayOps tool is not available")
    try:
        payload = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
        if "source" in TOOL_MODELS[name].model_fields: payload["source"] = selected_source
        arguments = TOOL_MODELS[name].model_validate(payload).model_dump()
        if name == "get_payment_details": arguments["source"] = selected_source
        result = TOOL_FUNCTIONS[name](session, **arguments)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        logger.warning("PayOps tool validation failed: tool=%s", name)
        raise AIToolError("The model supplied invalid tool arguments") from exc
    except AIToolError: raise
    except Exception as exc:
        logger.exception("PayOps tool failed: tool=%s", name)
        raise AIToolError("The PayOps data tool could not complete") from exc
    logger.info("PayOps tool completed: tool=%s duration_ms=%s", name, round((time.perf_counter() - started) * 1000, 1))
    return result
