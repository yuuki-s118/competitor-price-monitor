from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.price_alert import PriceAlert
    from app.models.price_snapshot import PriceSnapshot


class TrackedProduct(Base):
    """ユーザーが追跡登録した商品(特定ECサイト上の1商品ページに対応する)。"""

    __tablename__ = "tracked_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), nullable=False)

    external_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_url: Mapped[str] = mapped_column(String(500), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="tracked_product")
    price_alerts: Mapped[list["PriceAlert"]] = relationship(back_populates="tracked_product")
