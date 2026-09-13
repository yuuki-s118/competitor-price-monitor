from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.retailer import Retailer
from app.schemas.retailer import RetailerRead

router = APIRouter()


@router.get("", response_model=list[RetailerRead])
async def list_retailers(db: AsyncSession = Depends(get_db)) -> list[Retailer]:
    result = await db.scalars(select(Retailer).order_by(Retailer.id))
    return list(result.all())
