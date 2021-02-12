from datetime import date, datetime, timedelta
from pathlib import Path
from re import VERBOSE as re_VERBOSE
from re import Pattern
from re import compile as re_compile
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConstrainedStr
from yaml import safe_load

from invoicez.exceptions import InvoicezException

title_pattern_required_fields = frozenset(
    {"continuation", "company", "training", "extra"}
)


class StrippedLowercaseStr(ConstrainedStr):
    to_lower = True
    strip_whitespace = True


class Title(BaseModel):
    continuation: bool
    company: StrippedLowercaseStr
    training: StrippedLowercaseStr
    place: StrippedLowercaseStr
    extra: Optional[StrippedLowercaseStr]


class Event(BaseModel):
    continuation: bool
    company: StrippedLowercaseStr
    training: StrippedLowercaseStr
    place: StrippedLowercaseStr
    extra: Optional[StrippedLowercaseStr]
    description: Optional[StrippedLowercaseStr]
    link: str
    id: str
    start: Union[date, datetime]
    duration: timedelta

    @classmethod
    def from_gcal_event(
        cls, gcal_event: Dict[str, Any], title_pattern: Pattern
    ) -> Optional["Event"]:
        parsed_title = cls.parse_title(gcal_event["summary"], title_pattern)
        if parsed_title is None:
            return None
        start, duration = cls._process_dates(gcal_event)
        return cls(
            continuation=parsed_title.continuation,
            company=parsed_title.company,
            training=parsed_title.training,
            place=parsed_title.place,
            extra=parsed_title.extra,
            start=start,
            duration=duration,
            description=gcal_event.get("description"),
            link=gcal_event["htmlLink"],
            id=gcal_event["id"],
        )

    @staticmethod
    def compile_pattern(pattern: str) -> Pattern:
        compiled_pattern = re_compile(pattern, re_VERBOSE)
        missing_fields = title_pattern_required_fields.difference(
            compiled_pattern.groupindex.keys()
        )

        if missing_fields:
            raise InvoicezException(
                f"Title pattern doesn't contain the necessary fields {missing_fields}."
            )
        return compiled_pattern

    @staticmethod
    def parse_title(title: str, pattern: Pattern) -> Optional[Title]:
        match = pattern.match(title)
        if match is None:
            return None

        continuation = match.group("continuation") is not None
        company = match.group("company")
        training = match.group("training")
        place = match.group("place")
        extra = match.group("extra")
        return Title(
            continuation=continuation,
            company=company,
            training=training,
            place=place,
            extra=extra,
        )

    @staticmethod
    def _process_dates(
        gcal_event: Dict[str, Any]
    ) -> Tuple[Union[date, datetime], timedelta]:
        next(iter(gcal_event.get("start").values()))
        with_time = "dateTime" in gcal_event["start"]
        if with_time:
            start_datetime = datetime.fromisoformat(gcal_event["start"]["dateTime"])
            end_datetime = datetime.fromisoformat(gcal_event["end"]["dateTime"])
            duration = end_datetime - start_datetime
        else:
            start_date = date.fromisoformat(gcal_event["start"]["date"])
            end_date = date.fromisoformat(gcal_event["end"]["date"])
            duration = end_date - start_date
        return start_datetime if with_time else start_date, duration


class MergedEvent(BaseModel):
    company: str
    training: str
    place: str
    description: Optional[str]
    link: str
    id: str
    starts: List[Union[date, datetime]]
    durations: List[timedelta]


class Item(BaseModel):
    dates: List[date]
    description: str
    n: int
    unit_price: int


class Invoice(BaseModel):
    invoice_number: str
    description: str
    company: str
    ref: str
    date: date
    link: str
    event_id: str
    items: List[Item]

    @classmethod
    def all_from_ymls_dir(cls, ymls_dir: Path) -> List["Invoice"]:
        invoices = []
        for path in ymls_dir.glob("*.yml"):
            print(path)
            invoices.append(cls.parse_obj(safe_load(path.read_text(encoding="utf8"))))
        return invoices
