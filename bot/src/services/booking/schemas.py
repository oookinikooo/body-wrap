from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, model_validator


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    fullname: str
    reservation_at: datetime


class SessionAdd(BaseModel):
    date: date
    time: time
    user: User | None = None


class Session(SessionAdd):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def handle_flat_fields(cls, values):
        if isinstance(values, dict):
            if 'user' not in values or not values['user']:
                for key in ("user_id", "fullname", "reservation_at"):
                    if key in values and values[key] is not None:
                        continue
                    break
                else:
                    values['user'] = {
                        'id': values['user_id'],
                        'fullname': values['fullname'],
                        'reservation_at': values['reservation_at']
                    }
        return values
