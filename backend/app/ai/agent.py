import json
import logging
import time
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError
from sqlalchemy.orm import Session

from app.ai.dispatcher import dispatch_tool
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIToolError, AIToolRoundLimitError
from app.ai.prompts import PAYOPS_INSTRUCTIONS
from app.ai.schemas import CopilotResponse, EvidenceCitation
from app.ai.tool_schemas import OPENAI_TOOLS, TOOL_DESCRIPTIONS
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _item_dict(item: Any) -> dict:
    if hasattr(item, "model_dump"): return item.model_dump(exclude_none=True)
    if isinstance(item, dict): return item
    return {"type": getattr(item, "type", "function_call"), "call_id": getattr(item, "call_id", None), "name": getattr(item, "name", None), "arguments": getattr(item, "arguments", None)}


class PayOpsAgent:
    def __init__(self, settings: Settings | None = None, client: Any | None = None, max_tool_rounds: int = 6) -> None:
        self.settings = settings or get_settings(); self.max_tool_rounds = max_tool_rounds
        key = self.settings.openai_api_key.get_secret_value()
        if client is None and not key: raise AIConfigurationError("PayOps AI is not configured")
        self.client = client or OpenAI(api_key=key, timeout=self.settings.openai_timeout_seconds, max_retries=1)

    def query(self, session: Session, message: str, source: str) -> CopilotResponse:
        started = time.perf_counter(); tools_used: list[str] = []
        inputs: list[dict] = [{"role": "user", "content": f"Selected data source: {source}. User question: {message}"}]
        logger.info("PayOps AI request started: source=%s", source)
        try:
            for round_index in range(self.max_tool_rounds):
                response = self.client.responses.create(model=self.settings.openai_model, instructions=PAYOPS_INSTRUCTIONS, input=inputs, tools=OPENAI_TOOLS, tool_choice="auto", parallel_tool_calls=False, max_output_tokens=self.settings.openai_max_output_tokens, include=["reasoning.encrypted_content"], store=False)
                output = list(getattr(response, "output", [])); calls = [item for item in output if getattr(item, "type", None) == "function_call"]
                if not calls:
                    answer = str(getattr(response, "output_text", "") or "").strip()
                    if not answer: raise AIProviderError("PayOps AI returned no answer")
                    logger.info("PayOps AI request completed: tools=%s duration_ms=%s", tools_used, round((time.perf_counter() - started) * 1000, 1))
                    return CopilotResponse(answer=answer, source=source, tools_used=tools_used, citations=[EvidenceCitation(label=TOOL_DESCRIPTIONS[name]) for name in tools_used])
                if round_index == self.max_tool_rounds - 1: raise AIToolRoundLimitError("PayOps AI reached its tool-call limit")
                inputs.extend(_item_dict(item) for item in output)
                for call in calls:
                    name = str(getattr(call, "name", "")); result = dispatch_tool(session, name, str(getattr(call, "arguments", "{}")), source)
                    if name not in tools_used: tools_used.append(name)
                    inputs.append({"type": "function_call_output", "call_id": str(getattr(call, "call_id", "")), "output": json.dumps(result, default=str)})
        except (AIConfigurationError, AIToolError, AIToolRoundLimitError, AIProviderError): raise
        except AuthenticationError as exc: raise AIProviderError("OpenAI authentication failed") from exc
        except RateLimitError as exc: raise AIProviderError("PayOps AI is temporarily rate limited") from exc
        except (APITimeoutError, APIConnectionError) as exc: raise AIProviderError("PayOps AI is temporarily unreachable") from exc
        except APIError as exc: raise AIProviderError("PayOps AI provider request failed") from exc
        except Exception as exc:
            logger.exception("PayOps AI request failed")
            raise AIProviderError("PayOps AI could not complete the request") from exc
        raise AIToolRoundLimitError("PayOps AI reached its tool-call limit")
