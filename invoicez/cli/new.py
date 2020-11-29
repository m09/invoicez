from datetime import datetime, timedelta
from logging import getLogger
from pathlib import Path

from yaml import safe_dump as yaml_safe_dump, safe_load as yaml_safe_load

from invoicez.cli import command, dir_path_option, path_argument
from invoicez.paths import Paths


_logger = getLogger(__name__)


@command
@path_argument
@dir_path_option
def new(path: str, dir_path: str) -> None:
    """Create a new invoice based on an existing one."""
    paths = Paths(Path(dir_path))
    now = datetime.now()
    prefix = now.strftime("%Y-%m")
    date = now.strftime("%d/%m/%Y")
    limit_date = (now + timedelta(days=31)).strftime("%d/%m/%Y")
    n = len(list(paths.git_dir.glob(f"*/{prefix}-*.yml"))) + 1
    output_path = paths.working_dir / f"{prefix}-{n:03}.yml"
    with (paths.working_dir / path).open(encoding="utf8") as fh:
        content = yaml_safe_load(fh)
    content["date"] = date
    content["limit_date"] = limit_date
    _logger.info(
        f"Creating new invoice in {output_path.relative_to(paths.working_dir)}"
    )
    with output_path.open("w", encoding="utf8") as fh:
        yaml_safe_dump(content, fh, allow_unicode=True)
