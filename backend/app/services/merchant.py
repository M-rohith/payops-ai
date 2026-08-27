from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Merchant


def get_demo_merchant_id(session: Session) -> int:
    merchant_id = session.scalar(select(Merchant.id).where(Merchant.source == "demo").order_by(Merchant.id).limit(1))
    if merchant_id is None:
        raise HTTPException(status_code=503, detail="No merchant data found. Run the development seed command.")
    return merchant_id
