from pathlib import Path

from invoicez.building import Builder
from invoicez.paths import Paths
from invoicez.settings import Settings
from invoicez.target import Target


def run(path: Path, template: str, paths: Paths) -> None:
    settings = Settings.load(paths)
    target = Target(path, template, paths)
    Builder(target, settings, paths)
