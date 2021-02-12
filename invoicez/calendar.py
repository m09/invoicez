from logging import getLogger
from pickle import dump as pickle_dump, load as pickle_load
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rich.console import Console
from rich.prompt import IntPrompt
from rich.rule import Rule

from invoicez.paths import Paths


class Calendar:
    def __init__(self, paths: Paths):
        self._logger = getLogger(__name__)
        self._paths = paths
        self._service = self._build_service()

    def _build_service(self) -> Any:
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

    def _select_calendar(self) -> None:
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

    @property
    def _selected_calendar(self) -> str:
        if not self._paths.gcalendar_selected_calendar.exists():
            console = Console()
            console.print(
                "[bold yellow]No selected calendar. "
                "Starting the selection procedure.[/bold yellow]"
            )
            self._select_calendar()
        return self._paths.gcalendar_selected_calendar.read_text(encoding="utf8")

    @_selected_calendar.setter
    def _selected_calendar(self, value: str) -> None:
        self._paths.gcalendar_selected_calendar.parent.mkdir(
            parents=True, exist_ok=True
        )
        self._paths.gcalendar_selected_calendar.write_text(value, encoding="utf8")

    def _list_events(self) -> None:
        events = []
        next_sync_token = None
        page_token = None
        while next_sync_token is None:
            result = (
                self._service.events()
                .list(calendarId=self._selected_calendar, pageToken=page_token,)
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken", None)
            next_sync_token = result.get("nextSyncToken", None)

        print(next_sync_token, len(events))
        for event in events:
            print(
                "{}: {}-{}, {}".format(
                    event.get("summary"),
                    event.get("start"),
                    event.get("end"),
                    event.get("description"),
                )
            )
