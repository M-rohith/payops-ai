from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.agent import PayOpsAgent
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIToolError, AIToolRoundLimitError
from app.ai.schemas import CopilotQuery, CopilotResponse
from app.database import get_db

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotResponse)
def query_copilot(request: CopilotQuery, db: Session = Depends(get_db)) -> CopilotResponse:
    try: return PayOpsAgent().query(db, request.message, request.source)
    except AIConfigurationError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AIToolError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIToolRoundLimitError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AIProviderError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
