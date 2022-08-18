from pathlib import Path

from rich.console import Console

from invoicez.calendar import GoogleCalendar
from invoicez.cli import app
from invoicez.mapping import Mapper
from invoicez.merging import Merger
from invoicez.paths import Paths
from invoicez.settings import Settings


@app.command()
def main() -> None:
    paths = Paths(Path("."))
    settings = Settings.load(paths)

    console = Console()

    syncer = GoogleCalendar(paths, settings)
    events = syncer.list_events()

    merger = Merger(paths, settings)
    merged_events = merger.merge_events(events)

    mapper = Mapper(paths, settings)
    mapper.map(merged_events, console)
