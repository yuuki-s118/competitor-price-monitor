import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.price_collection import collect_all_active_prices

router = APIRouter()


def _verify_internal_secret(x_internal_secret: str = Header(default="")) -> None:
    if not settings.internal_task_secret or not hmac.compare_digest(
        x_internal_secret, settings.internal_task_secret
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@router.post("/collect-all-prices", dependencies=[Depends(_verify_internal_secret)])
async def collect_all_prices(db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    """有効な監視対象商品すべての価格を収集する。

    外部のスケジューラ(GitHub Actions)から呼び出す想定。
    """
    collected = await collect_all_active_prices(db)
    return {"collected": collected}
