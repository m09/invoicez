from pathlib import Path

from invoicez.calendar import Calendar
from invoicez.cli import command, dir_path_option
from invoicez.paths import Paths


@command
@dir_path_option
def sync(dir_path: str) -> None:
    """Synchronize with Google Calendar."""
    paths = Paths(Path(dir_path))
    calendar = Calendar(paths)
    calendar._list_events()
