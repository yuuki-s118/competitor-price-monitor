import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.notification_log import NotificationLog
    from app.models.tracked_product import TrackedProduct


class AlertRuleType(enum.StrEnum):
    PRICE_BELOW = "price_below"
    PRICE_DROP_PERCENT = "price_drop_percent"


class PriceAlert(Base):
    """価格変動を通知する条件。ユーザーが商品ごとに設定する。"""

    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_product_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rule_type: Mapped[AlertRuleType] = mapped_column(Enum(AlertRuleType), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tracked_product: Mapped["TrackedProduct"] = relationship(back_populates="price_alerts")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        back_populates="price_alert", cascade="all, delete-orphan", passive_deletes=True
    )
