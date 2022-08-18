from json import load
from pathlib import Path
from shutil import copytree
from typing import Any, List

from git import Repo
from pytest import fixture

from invoicez.calendar import Calendar
from invoicez.model import Event
from invoicez.paths import Paths
from invoicez.settings import Settings


@fixture
def assets_dir() -> Path:
    return Path(__file__).parent / "assets"


@fixture(autouse=True)
def working_dir(assets_dir: Path, tmp_path: Path, monkeypatch: Any) -> None:
    source_dir = assets_dir / "test_cli"
    working_dir = tmp_path / "data"
    copytree(source_dir, working_dir)
    Repo.init(str(working_dir))
    monkeypatch.chdir(working_dir)


class FakeCalendar(Calendar):
    def __init__(self, paths: Paths, settings: Settings, events_json: Path):
        self.events_json = events_json
        self.title_pattern = Event.compile_pattern(settings.title_pattern)

    def list_events(self) -> List[Event]:
        with self.events_json.open(encoding="utf8") as fh:
            events_json = load(fh)
        events = []
        for gcal_event in events_json:
            event = Event.from_gcal_event(gcal_event, self.title_pattern)
            if event is not None:
                events.append(event)
        return sorted(events, key=lambda e: e.start)


@fixture
def calendar(assets_dir: Path) -> FakeCalendar:
    paths = Paths(Path.cwd())
    settings = Settings.load(paths)
    return FakeCalendar(paths, settings, assets_dir / "events.json")
