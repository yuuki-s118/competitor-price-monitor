from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_snapshot import PriceSnapshot
from app.models.tracked_product import TrackedProduct
from app.services.rakuten import fetch_item_price


async def collect_price(db: AsyncSession, product: TrackedProduct) -> PriceSnapshot:
    """指定した監視対象商品の現在価格を楽天から取得し、スナップショットとして保存する。

    APIエンドポイント(手動トリガー)とCeleryタスク(定期実行)の両方から使う共通ロジック。
    """
    price = await fetch_item_price(product.external_product_id)

    snapshot = PriceSnapshot(tracked_product_id=product.id, price=price)
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot
