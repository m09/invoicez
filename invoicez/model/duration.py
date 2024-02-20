from datetime import timedelta
from enum import Enum

from pydantic import BaseModel


class DurationUnit(str, Enum):
    day = "day"
    half_day = "half-day"


class Duration(BaseModel):
    n: int
    unit: DurationUnit

    @property
    def timedelta(self) -> timedelta:
        return timedelta(hours=self.n * (24 if self.unit is DurationUnit.day else 3))
