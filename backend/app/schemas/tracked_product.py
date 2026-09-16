from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrackedProductCreate(BaseModel):
    retailer_id: int
    external_product_id: str
    name: str
    product_url: str
    image_url: str | None = None


class TrackedProductUpdate(BaseModel):
    name: str | None = None
    external_product_id: str | None = None
    product_url: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class TrackedProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    retailer_id: int
    external_product_id: str
    name: str
    product_url: str
    image_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
