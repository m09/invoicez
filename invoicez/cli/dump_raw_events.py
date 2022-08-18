from collections import defaultdict
from json import dump
from logging import INFO, basicConfig
from pathlib import Path
from typing import DefaultDict, Dict

from rich.logging import RichHandler
from yaml import safe_dump, safe_load

from invoicez.calendar import GoogleCalendar
from invoicez.cli import app
from invoicez.model import Event
from invoicez.paths import Paths
from invoicez.settings import Settings


@app.command()
def dump_raw_events(output: Path, for_tests: bool = True) -> None:
    basicConfig(
        level=INFO,
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    paths = Paths(Path("."))

    settings = Settings.load(paths)
    calendar = GoogleCalendar(paths, settings)
    raw_events = calendar.list_raw_events()

    if for_tests:
        title_pattern = Event.compile_pattern(settings.title_pattern)

        fields_to_keep = {"start", "end"}

        companies: Dict[str, str] = {}
        trainings: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        extras: Dict[str, str] = {}
        ids: Dict[str, str] = {}
        html_links: Dict[str, str] = {}
        refs: Dict[str, str] = {}

        modified_events = []
        for raw_event in raw_events:
            parsed_title = Event.parse_title(raw_event["summary"], title_pattern)
            if parsed_title is None:
                continue
            event = {}
            continuation = "-> " if parsed_title.continuation else ""
            new_company = companies.setdefault(
                parsed_title.company, f"Company_{len(companies)}"
            )
            new_training = trainings[parsed_title.company].setdefault(
                parsed_title.training,
                f"Training_{len(trainings[parsed_title.company])}",
            )
            new_place = parsed_title.place
            if parsed_title.extra:
                new_extra = " - "
                new_extra += extras.setdefault(
                    parsed_title.extra, f"Extra_{len(extras)}"
                )
            else:
                new_extra = ""

            event[
                "summary"
            ] = f"{continuation}{new_company} - {new_training} - {new_place}{new_extra}"
            event["id"] = ids.setdefault(raw_event["id"], f"Id_{len(ids)}")
            event["htmlLink"] = html_links.setdefault(
                raw_event["htmlLink"], f"HTMLLink_{len(html_links)}"
            )
            if "description" in raw_event:
                description = safe_load(raw_event.get("description"))
                if "ref" in description:
                    description["ref"] = refs.setdefault(
                        description["ref"], f"Ref_{len(refs)}"
                    )
                event["description"] = safe_dump(description)
            for field in fields_to_keep:
                event[field] = raw_event.get(field)
            modified_events.append(event)
        raw_events = modified_events

    with output.open("w", encoding="utf8") as fh:
        dump(raw_events, fh)
