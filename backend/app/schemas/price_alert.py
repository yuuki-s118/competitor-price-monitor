from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.price_alert import AlertRuleType


class PriceAlertCreate(BaseModel):
    rule_type: AlertRuleType
    threshold_value: Decimal


class PriceAlertUpdate(BaseModel):
    threshold_value: Decimal | None = None
    is_active: bool | None = None


class PriceAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_product_id: int
    rule_type: AlertRuleType
    threshold_value: Decimal
    is_active: bool
    created_at: datetime
