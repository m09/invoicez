from datetime import date, datetime, timedelta
from enum import Enum
from io import StringIO
from pathlib import Path
from re import VERBOSE as re_VERBOSE
from re import Pattern
from re import compile as re_compile
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from pydantic import BaseModel, ConstrainedStr, root_validator, validator
from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from yaml import safe_dump, safe_load

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

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        panel = Panel(
            self.description or "Pas de détail",
            title=f"[bold][blue]{self.company}[/] ⋅ [red]{self.training}[/][/]",
        )
        yield panel


class DurationUnit(str, Enum):
    day = "day"
    half_day = "half-day"
    hour = "hour"


class Date(BaseModel):
    start: List[date]
    duration: Optional[List[Union[int, float]]]
    duration_unit: DurationUnit = DurationUnit.day

    class Config:
        use_enum_values = True

    @validator("start", "duration", pre=True)
    def transform_str_to_list_singleton(cls, v: Union[str, List[str]]) -> List[str]:
        return v if isinstance(v, list) else [v]

    @validator("duration")
    def check_start_and_duration_match(
        cls,
        v: List[Union[int, float]],
        values: Dict[str, Any],
    ) -> List[Union[int, float]]:
        if "start" in values and len(v) != len(values["start"]):
            raise ValueError("duration and start lists must be of equal length")
        return v


class Item(BaseModel):
    date: Optional[Date]
    description: str
    n: int
    unit_price: int

    @validator("date", pre=True)
    def transform_date_to_dict(cls, v: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        return v if isinstance(v, dict) else dict(start=v)

    @root_validator(pre=True)
    def fill_duration_with_n_if_necessary(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if "date" in values:
            d = values["date"]
            if d is not None and isinstance(d, dict) and d.get("duration") is None:
                values["date"]["duration"] = values["n"]
        return values


class GcalInfo(BaseModel):
    link: str
    event_id: str


class Invoice(BaseModel):
    path: Path
    invoice_number: str
    description: str
    company: str
    ref: str
    date: date
    gcal_info: Optional[GcalInfo]
    items: List[Item]

    @classmethod
    def all_from_ymls_dir(cls, ymls_dir: Path) -> Iterator["Invoice"]:
        for path in sorted(ymls_dir.glob("*.yml")):
            data = safe_load(path.read_text(encoding="utf8"))
            data["path"] = path
            yield cls.parse_obj(data)

    def dct(self) -> Dict[str, Any]:
        return self.dict(
            exclude={"path"},
            exclude_unset=True,
            exclude_none=True,
            exclude_defaults=True,
        )

    def yml(self) -> str:
        with StringIO() as string_io:
            safe_dump(
                self.dct(), string_io, allow_unicode=True, default_flow_style=False
            )
            return string_io.getvalue()

    def write(self) -> None:
        with self.path.open(mode="w", encoding="utf8") as fh:
            fh.write(self.yml())
