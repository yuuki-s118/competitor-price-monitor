from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification_log import NotificationChannel


class NotificationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price_alert_id: int
    price_snapshot_id: int
    channel: NotificationChannel
    sent_at: datetime
