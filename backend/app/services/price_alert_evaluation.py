import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_log import NotificationChannel, NotificationLog
from app.models.price_alert import AlertRuleType, PriceAlert
from app.models.price_snapshot import PriceSnapshot
from app.models.tracked_product import TrackedProduct
from app.models.user import User
from app.services.notifications import NotificationError, send_alert_email

logger = logging.getLogger(__name__)


def _price_below_triggered(alert: PriceAlert, price: Decimal) -> bool:
    return price <= alert.threshold_value


def _price_drop_percent_triggered(
    alert: PriceAlert, current_price: Decimal, previous_price: Decimal | None
) -> bool:
    if previous_price is None or previous_price == 0:
        return False
    drop_percent = (previous_price - current_price) / previous_price * 100
    return drop_percent >= alert.threshold_value


def _is_triggered(
    alert: PriceAlert, current_price: Decimal, previous_price: Decimal | None
) -> bool:
    if alert.rule_type == AlertRuleType.PRICE_BELOW:
        return _price_below_triggered(alert, current_price)
    if alert.rule_type == AlertRuleType.PRICE_DROP_PERCENT:
        return _price_drop_percent_triggered(alert, current_price, previous_price)
    return False


async def evaluate_price_alerts(
    db: AsyncSession, product: TrackedProduct, snapshot: PriceSnapshot
) -> None:
    """新しい価格スナップショットに対して、有効なアラート条件を評価し、条件を満たせば通知する。

    PRICE_BELOW は状態(閾値以下かどうか)なので、直前のスナップショットも既に条件を
    満たしていた場合は再通知しない(閾値を下回った瞬間だけ通知する)。
    PRICE_DROP_PERCENT は直近2点間の変化そのものが通知対象のため、条件を満たす度に通知する。
    """
    result = await db.scalars(
        select(PriceAlert).where(
            PriceAlert.tracked_product_id == product.id,
            PriceAlert.is_active,
        )
    )
    alerts = list(result.all())
    if not alerts:
        return

    previous_snapshot = await db.scalar(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.tracked_product_id == product.id,
            PriceSnapshot.id != snapshot.id,
        )
        .order_by(PriceSnapshot.scraped_at.desc())
        .limit(1)
    )
    previous_price = previous_snapshot.price if previous_snapshot else None

    for alert in alerts:
        if not _is_triggered(alert, snapshot.price, previous_price):
            continue
        if (
            alert.rule_type == AlertRuleType.PRICE_BELOW
            and previous_price is not None
            and _price_below_triggered(alert, previous_price)
        ):
            continue
        await _notify(db, product, alert, snapshot)


async def _notify(
    db: AsyncSession, product: TrackedProduct, alert: PriceAlert, snapshot: PriceSnapshot
) -> None:
    user = await db.get(User, product.user_id)
    if user is None:
        return

    subject = f"[価格アラート] {product.name}"
    body = (
        f"{product.name} が価格アラート条件を満たしました。\n\n"
        f"現在価格: {snapshot.price} {snapshot.currency}\n"
        f"商品ページ: {product.product_url}"
    )

    try:
        await send_alert_email(user.email, subject, body)
    except NotificationError:
        logger.exception("通知メールの送信に失敗しました: tracked_product_id=%s", product.id)
        return

    db.add(
        NotificationLog(
            price_alert_id=alert.id,
            price_snapshot_id=snapshot.id,
            channel=NotificationChannel.EMAIL,
        )
    )
    await db.commit()
