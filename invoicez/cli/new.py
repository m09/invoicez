from datetime import datetime
from logging import getLogger
from pathlib import Path

from click import argument
from yaml import safe_dump as yaml_safe_dump, safe_load as yaml_safe_load

from invoicez.cli import command, dir_path_option, path_argument
from invoicez.config import get_config
from invoicez.paths import Paths


_logger = getLogger(__name__)


@command
@path_argument
@argument("name")
@dir_path_option
def new(path: str, name: str, dir_path: str) -> None:
    """Create a new invoice based on an existing one."""
    paths = Paths(Path(dir_path))
    config = get_config(paths)

    # Load invoice on which to base the new one
    content = yaml_safe_load((paths.working_dir / path).read_text(encoding="utf8"))

    invoice_number = _get_next_invoice_number(paths)
    output_name = (
        config["name_template"]
        .replace("{name}", name)
        .replace("{company}", config["companies"][content["company"]]["name"])
        .replace("{invoice_number}", invoice_number)
    )
    output_path = (paths.working_dir / output_name).with_suffix(".yml")

    now = datetime.now()
    date = now.strftime("%d/%m/%Y")

    content["date"] = date
    content["invoice_number"] = invoice_number
    _logger.info(
        f"Creating new invoice in {output_path.relative_to(paths.working_dir)}"
    )
    with output_path.open("w", encoding="utf8") as fh:
        yaml_safe_dump(content, fh, allow_unicode=True)


def _get_next_invoice_number(paths: Paths) -> str:
    now = datetime.now()
    prefix = now.strftime("%Y-%m")
    n_invoices = 0
    for item in paths.git_dir.glob("**/*.yml"):
        content = yaml_safe_load(item.read_text(encoding="utf8"))
        if "invoice_number" in content and content["invoice_number"].startswith(prefix):
            n_invoices += 1
    return f"{prefix}-{n_invoices + 1:03}"
