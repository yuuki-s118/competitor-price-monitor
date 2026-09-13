import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_snapshot import PriceSnapshot
from app.models.tracked_product import TrackedProduct
from app.services.price_alert_evaluation import evaluate_price_alerts
from app.services.rakuten import RakutenAPIError, fetch_item_price

logger = logging.getLogger(__name__)


async def collect_price(db: AsyncSession, product: TrackedProduct) -> PriceSnapshot:
    """指定した監視対象商品の現在価格を楽天から取得し、スナップショットとして保存する。

    APIエンドポイント(手動トリガー)・Celeryタスク・定期収集トリガー(本番)の
    いずれからも使う共通ロジック。保存後、有効な価格アラート条件を評価し、
    条件を満たせば通知する。
    """
    price = await fetch_item_price(product.external_product_id)

    snapshot = PriceSnapshot(tracked_product_id=product.id, price=price)
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    await evaluate_price_alerts(db, product, snapshot)
    return snapshot


async def collect_all_active_prices(db: AsyncSession) -> int:
    """有効な監視対象商品すべての価格を収集する。1商品の失敗が他に影響しないようにする。

    本番(Render)では常時稼働のCeleryワーカーを使わず、GitHub Actionsの
    スケジュール実行からこの関数を直接呼び出すエンドポイント経由で定期収集している。
    """
    result = await db.scalars(select(TrackedProduct).where(TrackedProduct.is_active))
    products = list(result.all())

    for product in products:
        try:
            await collect_price(db, product)
        except RakutenAPIError:
            logger.exception("価格取得に失敗しました: tracked_product_id=%s", product.id)

    return len(products)
