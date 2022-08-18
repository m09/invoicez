from datetime import date
from logging import getLogger
from typing import Dict, Optional

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
    rates: Optional[str]
    name: str
    company: str


class InvoiceStrings(BaseModel):
    class Config:
        extra = Extra.allow

    training_day: str
    half_training_day: str
    description: str


class Strings(BaseModel):
    invoice: InvoiceStrings


class Settings(BaseModel):
    class Config:
        extra = Extra.allow

    start_date: date = date.min
    invoice_name_format_string: str
    title_pattern: str
    companies: Dict[str, Company]
    trainings: Dict[str, Training]
    rates: Dict[str, Rates]
    strings: Strings

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
        training_rates = self.rates[company].trainings
        if rates is None:
            if "default" not in training_rates:
                raise InvoicezException(
                    f"No rates are used for at least one training of company {company}"
                    f", but no default rates were provided in "
                    f"settings.yml > rates > {company} > trainings > default"
                )
            return training_rates["default"]
        if rates not in training_rates:
            raise InvoicezException(
                f"Could not find rates {rates} in "
                f"settings.yml > rates > {company} > trainings > default"
            )
        return training_rates[rates]
