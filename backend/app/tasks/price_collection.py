import asyncio
import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import celery_session_factory
from app.models.tracked_product import TrackedProduct
from app.services.price_collection import collect_price
from app.services.rakuten import RakutenAPIError

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]


@celery_app.task(name="tasks.collect_price_for_product")
def collect_price_for_product(product_id: int) -> None:
    asyncio.run(_collect_price_for_product(product_id))


async def _collect_price_for_product(
    product_id: int, session_factory: SessionFactory = celery_session_factory
) -> None:
    async with session_factory() as db:
        product = await db.get(TrackedProduct, product_id)
        if product is None or not product.is_active:
            return

        try:
            await collect_price(db, product)
        except RakutenAPIError:
            logger.exception("価格取得に失敗しました: tracked_product_id=%s", product_id)


@celery_app.task(name="tasks.collect_all_active_prices")
def collect_all_active_prices() -> None:
    """有効な監視対象商品それぞれについて、価格取得タスクを個別にキューへ積む。

    1商品の失敗が他の商品の収集を止めないよう、ここでは実際の取得は行わず配信のみ行う。
    """
    asyncio.run(_dispatch_all_active_products())


async def _dispatch_all_active_products(
    session_factory: SessionFactory = celery_session_factory,
) -> None:
    async with session_factory() as db:
        result = await db.scalars(select(TrackedProduct.id).where(TrackedProduct.is_active))
        product_ids = list(result.all())

    for product_id in product_ids:
        collect_price_for_product.delay(product_id)
