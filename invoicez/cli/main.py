from pathlib import Path

from invoicez.cli import app
from invoicez.mapping import Mapper
from invoicez.merging import Merger
from invoicez.paths import Paths
from invoicez.settings import Settings
from invoicez.syncing import GoogleCalendarSyncer


@app.command()
def main() -> None:
    paths = Paths(Path("."))
    settings = Settings.load(paths)

    syncer = GoogleCalendarSyncer(paths, settings)
    events = syncer.list_events()

    merger = Merger(paths, settings)
    merged_events = merger.merge_events(events)

    mapper = Mapper(paths)
    mapper.map(merged_events)
