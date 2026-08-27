from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.exceptions import RazorpayAuthenticationError, RazorpayError, RazorpayNotConfiguredError
from app.integrations.razorpay.schemas import ConnectionStatus, SyncSummary
from app.integrations.razorpay.status import connection_status
from app.integrations.razorpay.sync import synchronize

router = APIRouter(prefix="/api/integrations/razorpay", tags=["integrations"])


@router.get("/status", response_model=ConnectionStatus)
def status() -> ConnectionStatus:
    return connection_status()


@router.post("/sync", response_model=SyncSummary)
def sync(count: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)) -> SyncSummary:
    settings = get_settings()
    if not settings.razorpay_key_id.startswith("rzp_test_"):
        raise HTTPException(status_code=400, detail="Manual sync requires Razorpay Test Mode credentials")
    try: return synchronize(db, RazorpayClient(settings), count)
    except RazorpayNotConfiguredError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RazorpayAuthenticationError as exc: raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RazorpayError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
