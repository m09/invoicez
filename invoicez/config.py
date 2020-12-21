from logging import getLogger
from typing import Any, Dict

from yaml import safe_load as yaml_safe_load

from invoicez.paths import Paths


_logger = getLogger(__name__)


def get_config(paths: Paths) -> Dict[str, Any]:
    return yaml_safe_load(paths.config.read_text(encoding="utf8"))
