from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification_log import NotificationLog
from app.models.price_alert import PriceAlert
from app.models.price_snapshot import PriceSnapshot
from app.models.retailer import Retailer
from app.models.tracked_product import TrackedProduct
from app.models.user import User
from app.schemas.notification_log import NotificationLogRead
from app.schemas.price_alert import PriceAlertCreate, PriceAlertRead, PriceAlertUpdate
from app.schemas.price_snapshot import PriceSnapshotRead
from app.schemas.tracked_product import (
    TrackedProductCreate,
    TrackedProductRead,
    TrackedProductUpdate,
)
from app.services.price_collection import collect_price as collect_price_for_product
from app.services.rakuten import RakutenAPIError

router = APIRouter()


async def _get_owned_product(
    product_id: int, current_user: User, db: AsyncSession
) -> TrackedProduct:
    product = await db.get(TrackedProduct, product_id)
    if product is None or product.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")
    return product


async def _get_owned_alert(
    product_id: int, alert_id: int, current_user: User, db: AsyncSession
) -> PriceAlert:
    await _get_owned_product(product_id, current_user, db)
    alert = await db.get(PriceAlert, alert_id)
    if alert is None or alert.tracked_product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="アラートが見つかりません"
        )
    return alert


@router.post("", response_model=TrackedProductRead, status_code=status.HTTP_201_CREATED)
async def create_tracked_product(
    product_in: TrackedProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedProduct:
    retailer = await db.get(Retailer, product_in.retailer_id)
    if retailer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="retailer_id が存在しません"
        )

    product = TrackedProduct(user_id=current_user.id, **product_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=list[TrackedProductRead])
async def list_tracked_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrackedProduct]:
    result = await db.scalars(
        select(TrackedProduct)
        .where(TrackedProduct.user_id == current_user.id)
        .order_by(TrackedProduct.id)
    )
    return list(result.all())


@router.get("/{product_id}", response_model=TrackedProductRead)
async def get_tracked_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedProduct:
    return await _get_owned_product(product_id, current_user, db)


@router.patch("/{product_id}", response_model=TrackedProductRead)
async def update_tracked_product(
    product_id: int,
    product_in: TrackedProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedProduct:
    product = await _get_owned_product(product_id, current_user, db)

    for field, value in product_in.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracked_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    product = await _get_owned_product(product_id, current_user, db)
    await db.delete(product)
    await db.commit()


@router.post(
    "/{product_id}/collect-price",
    response_model=PriceSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def collect_price(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceSnapshot:
    """楽天ウェブサービスから現在価格を取得し、価格スナップショットとして保存する。"""
    product = await _get_owned_product(product_id, current_user, db)

    try:
        return await collect_price_for_product(db, product)
    except RakutenAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{product_id}/price-snapshots", response_model=list[PriceSnapshotRead])
async def list_price_snapshots(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PriceSnapshot]:
    await _get_owned_product(product_id, current_user, db)

    result = await db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.tracked_product_id == product_id)
        .order_by(PriceSnapshot.scraped_at.desc())
    )
    return list(result.all())


@router.post(
    "/{product_id}/alerts", response_model=PriceAlertRead, status_code=status.HTTP_201_CREATED
)
async def create_price_alert(
    product_id: int,
    alert_in: PriceAlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceAlert:
    await _get_owned_product(product_id, current_user, db)

    alert = PriceAlert(tracked_product_id=product_id, **alert_in.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/{product_id}/alerts", response_model=list[PriceAlertRead])
async def list_price_alerts(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PriceAlert]:
    await _get_owned_product(product_id, current_user, db)

    result = await db.scalars(
        select(PriceAlert)
        .where(PriceAlert.tracked_product_id == product_id)
        .order_by(PriceAlert.id)
    )
    return list(result.all())


@router.patch("/{product_id}/alerts/{alert_id}", response_model=PriceAlertRead)
async def update_price_alert(
    product_id: int,
    alert_id: int,
    alert_in: PriceAlertUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceAlert:
    alert = await _get_owned_alert(product_id, alert_id, current_user, db)

    for field, value in alert_in.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{product_id}/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price_alert(
    product_id: int,
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    alert = await _get_owned_alert(product_id, alert_id, current_user, db)
    await db.delete(alert)
    await db.commit()


@router.get("/{product_id}/notification-logs", response_model=list[NotificationLogRead])
async def list_notification_logs(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationLog]:
    await _get_owned_product(product_id, current_user, db)

    result = await db.scalars(
        select(NotificationLog)
        .join(PriceAlert, NotificationLog.price_alert_id == PriceAlert.id)
        .where(PriceAlert.tracked_product_id == product_id)
        .order_by(NotificationLog.sent_at.desc())
    )
    return list(result.all())
