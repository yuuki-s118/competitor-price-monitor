from pydantic import BaseModel, ConfigDict


class RetailerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    base_url: str
