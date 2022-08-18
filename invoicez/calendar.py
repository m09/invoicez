from functools import cached_property
from logging import getLogger
from pickle import dump as pickle_dump
from pickle import load as pickle_load
from typing import Any, Dict, List

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rich.console import Console
from rich.prompt import IntPrompt
from rich.rule import Rule

from invoicez.model import Event
from invoicez.paths import Paths
from invoicez.settings import Settings


class Calendar:
    def __init__(self, paths: Paths):
        self._paths = paths

    def list_events(self) -> List[Event]:
        raise NotImplementedError(
            "This class should only be used through its implementations."
        )

    def list_raw_events(self) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "This class should only be used through its implementations."
        )

    def edit_event_description(self, event_id: str, new_description: str) -> None:
        raise NotImplementedError(
            "This class should only be used through its implementations."
        )

    def select_calendar(self) -> None:
        raise NotImplementedError(
            "This class should only be used through its implementations."
        )


class GoogleCalendar(Calendar):
    def __init__(self, paths: Paths, settings: Settings):
        super().__init__(paths)
        self._logger = getLogger(__name__)
        self._title_pattern = Event.compile_pattern(settings.title_pattern)

    def list_events(self) -> List[Event]:
        events = []
        for raw_event in self.list_raw_events():
            event = Event.from_gcal_event(raw_event, self._title_pattern)
            if event is not None:
                events.append(event)

        return sorted(events, key=lambda e: e.start)

    def list_raw_events(self) -> List[Dict[str, Any]]:
        events = []
        next_sync_token = None
        page_token = None
        while next_sync_token is None:
            result = (
                self._service.events()
                .list(calendarId=self._selected_calendar, pageToken=page_token)
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken", None)
            next_sync_token = result.get("nextSyncToken", None)
        return events

    def edit_event_description(self, event_id: str, new_description: str) -> None:
        self._service.events().patch(
            calendarId=self._selected_calendar,
            eventId=event_id,
            body=dict(description=new_description),
        ).execute()

    def select_calendar(self) -> None:
        calendars = []
        next_sync_token = None
        page_token = None
        while next_sync_token is None:
            result = self._service.calendarList().list(pageToken=page_token).execute()
            calendars.extend(result.get("items", []))
            page_token = result.get("nextPageToken", None)
            next_sync_token = result.get("nextSyncToken", None)

        console = Console()
        calendars_markdown_list = "\n".join(
            f"[bold yellow]{i}[/bold yellow]. {calendar['summary']}"
            for i, calendar in enumerate(calendars, start=1)
        )
        console.print(Rule(":date: Available calendars", align="left"))
        console.print()
        console.print(calendars_markdown_list)
        console.print()
        console.print(Rule(":pushpin: Selection", align="left"))
        console.print()
        calendar_index = (
            IntPrompt.ask(
                "Please enter the number that corresponds to the calendar to use",
                choices=list(map(str, range(1, len(calendars) + 1))),
                show_choices=False,
            )
            - 1
        )
        selected_calendar = calendars[calendar_index]
        self._selected_calendar = selected_calendar["id"]
        console.print()
        console.print(
            f":ok_hand: Calendar [bold]{calendars[calendar_index]['summary']}[/bold] "
            "is selected."
        )

    @cached_property
    def _service(self) -> Any:
        if self._paths.gcalendar_credentials.is_file():
            with self._paths.gcalendar_credentials.open("rb") as fh:
                creds = pickle_load(fh)
        else:
            creds = None

        if not creds or not creds.valid:
            ok = False
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    ok = True
                except RefreshError:
                    self._logger.warn("Could not refresh auth token")
            if not ok:
                scopes = [
                    "https://www.googleapis.com/auth/calendar.events",
                    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
                ]
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._paths.gcalendar_secrets, scopes
                )
                creds = flow.run_local_server(port=0)
            with self._paths.gcalendar_credentials.open("wb") as fh:
                pickle_dump(creds, fh)

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    @property
    def _selected_calendar(self) -> str:
        if not self._paths.gcalendar_selected_calendar.exists():
            console = Console()
            console.print(
                "[bold yellow]No selected calendar. "
                "Starting the selection procedure.[/bold yellow]"
            )
            self.select_calendar()
        return self._paths.gcalendar_selected_calendar.read_text(encoding="utf8")

    @_selected_calendar.setter
    def _selected_calendar(self, value: str) -> None:
        self._paths.gcalendar_selected_calendar.parent.mkdir(
            parents=True, exist_ok=True
        )
        self._paths.gcalendar_selected_calendar.write_text(value, encoding="utf8")
