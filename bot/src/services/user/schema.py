from datetime import datetime

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    fullname: str
    is_active: bool
    created_at: datetime
