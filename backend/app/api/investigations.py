from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.investigations import InvestigationItem
from app.services.investigations import get_investigations

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=list[InvestigationItem])
def investigations(
    source: Literal["demo", "razorpay", "all"] = Query("all"),
    db: Session = Depends(get_db),
) -> list[InvestigationItem]:
    """Prioritize existing operational evidence without mutating financial state."""
    return get_investigations(db, source)
