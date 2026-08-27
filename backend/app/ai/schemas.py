from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["all", "demo", "razorpay"]


class CopilotQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=2, max_length=2000)
    source: Source = "all"


class EvidenceCitation(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    label: str


class CopilotResponse(BaseModel):
    answer: str
    source: Source
    tools_used: list[str]
    citations: list[EvidenceCitation]
    advisory: bool = True
