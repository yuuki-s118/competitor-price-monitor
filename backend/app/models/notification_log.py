import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.price_alert import PriceAlert


class NotificationChannel(enum.StrEnum):
    EMAIL = "email"


class NotificationLog(Base):
    """実際に送信された通知の記録。どのアラート・どの価格スナップショットが引き金だったかを残す。"""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    price_alert_id: Mapped[int] = mapped_column(
        ForeignKey("price_alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("price_snapshots.id", ondelete="CASCADE"), nullable=False
    )

    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    price_alert: Mapped["PriceAlert"] = relationship(back_populates="notification_logs")
