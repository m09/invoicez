from typing import Iterable, List

from invoicez.model import Invoice, MergedEvent
from invoicez.paths import Paths


class Mapper:
    def __init__(self, paths: Paths):
        self._paths = paths

    def find_unmapped(self) -> None:
        pass

    @property
    def gcal_invoices(self) -> List[Invoice]:
        if not hasattr(self, "_gcal_invoices"):
            self._gcal_invoices = Invoice.all_from_ymls_dir(self._paths.gcal_ymls_dir)
        return self._gcal_invoices

    @property
    def extra_invoices(self) -> List[Invoice]:
        if not hasattr(self, "_extra_invoices"):
            self._extra_invoices = Invoice.all_from_ymls_dir(self._paths.extra_ymls_dir)
        return self._extra_invoices

    def map(self, merged_events: Iterable[MergedEvent]) -> None:
        print(self.gcal_invoices)
        print(self.extra_invoices)
        for merged_event in merged_events:
            print(repr(merged_event))
            print()
