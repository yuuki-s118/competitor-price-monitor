from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_product_id: int
    price: Decimal
    currency: str
    scraped_at: datetime
