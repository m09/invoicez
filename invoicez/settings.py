from logging import getLogger
from typing import Dict

from pydantic import BaseModel, Extra
from yaml import safe_load as yaml_safe_load

from invoicez.exceptions import InvoicezException
from invoicez.paths import Paths

_logger = getLogger(__name__)


class TrainingRates(BaseModel):
    training_day: int
    preparation_day: int


class Rates(BaseModel):
    trainings: Dict[str, TrainingRates]
    places: Dict[str, int]


class Company(BaseModel):
    class Config:
        extra = Extra.allow

    name: str
    maximum_days: int = 30


class Training(BaseModel):
    rates: str
    name: str
    company: str


class FormatStrings(BaseModel):
    invoice_training_day: str
    invoice_half_training_day: str
    invoice_description: str


class Settings(BaseModel):
    class Config:
        extra = Extra.allow

    title_pattern: str
    companies: Dict[str, Company]
    trainings: Dict[str, Training]
    rates: Dict[str, Rates]
    strings: FormatStrings

    @classmethod
    def load(cls, paths: Paths) -> "Settings":
        return cls.parse_obj(yaml_safe_load(paths.config.read_text(encoding="utf8")))

    def get_training(self, training: str) -> Training:
        if training not in self.trainings:
            raise InvoicezException(f"Couldn't find {training} in settings > trainings")
        return self.trainings[training]

    def get_training_rates(self, company: str, rates: str) -> TrainingRates:
        if company not in self.rates:
            raise InvoicezException(f"Couldn't find {company} in settings > rates")
        if rates not in self.rates[company].trainings:
            raise InvoicezException(
                f"Couldn't find {rates} in settings.yml > rates > {company} > trainings"
            )
        return self.rates[company].trainings[rates]
