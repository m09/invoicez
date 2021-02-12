from logging import getLogger
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import InvalidGitRepositoryError

from invoicez.exceptions import InvoicezException

_logger = getLogger(__name__)


class Paths:
    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir.resolve()

        self.pdfs_dir = self.git_dir / "pdfs"
        self.gcal_ymls_dir = self.git_dir / "gcal-ymls"
        self.extra_ymls_dir = self.git_dir / "extra-ymls"
        self.templates_dir = self.git_dir / "templates"
        self.config = self.git_dir / "config.yml"

        # Hidden stuff
        self.invoicez_dir = self.git_dir / ".invoicez"
        self.build_dir = self.invoicez_dir / "build"
        self.gcalendar_secrets = self.invoicez_dir / "gcalendar-secrets.json"
        self.gcalendar_selected_calendar = self.invoicez_dir / "selected-calendar.txt"
        self.gcalendar_credentials = self.invoicez_dir / "gcalendar-credentials.pickle"

    @property
    def git_dir(self) -> Optional[Path]:
        if not hasattr(self, "_git_dir"):
            try:
                repository = Repo(str(self.working_dir), search_parent_directories=True)
            except InvalidGitRepositoryError as e:
                raise InvoicezException(
                    "Could not find the path of the current git working directory. "
                    "Are you in one?"
                ) from e
            self._git_dir = Path(repository.git.rev_parse("--show-toplevel")).resolve()
        return self._git_dir
