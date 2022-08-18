from datetime import date
from shutil import copy2
from tempfile import NamedTemporaryFile
from typing import Iterable, Iterator, List, Tuple

from rich.columns import Columns
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from typer import launch
from yaml import safe_dump, safe_load

from invoicez.billing import Biller
from invoicez.model import Invoice, MergedEvent
from invoicez.paths import Paths
from invoicez.settings import Settings


class Mapper:
    def __init__(self, paths: Paths, settings: Settings):
        self._paths = paths
        self._settings = settings

    @property
    def _gcal_invoices(self) -> Iterator[Invoice]:
        return Invoice.all_from_ymls_dir(self._paths.gcal_ymls_dir)

    @property
    def _extra_invoices(self) -> Iterator[Invoice]:
        return Invoice.all_from_ymls_dir(self._paths.extra_ymls_dir)

    @property
    def _linked_gcal_invoices(self) -> Iterator[Invoice]:
        for invoice in self._gcal_invoices:
            if invoice.gcal_info is not None:
                yield invoice

    @property
    def _unlinked_gcal_invoices(self) -> Iterator[Invoice]:
        for invoice in self._gcal_invoices:
            if invoice.gcal_info is None:
                yield invoice

    def map(self, merged_events: Iterable[MergedEvent], console: Console) -> None:
        console.print("[b u blue]Detecting and deleting invalid Google Calendar IDs[/]")
        invalid_invoices = self._delete_invalid_gcal_infos(merged_events)
        if invalid_invoices:
            console.print(
                "Deleted invalid Google Calendar IDs for the following invoices:"
            )
            console.print(
                "\n".join(f"- {invoice.invoice_number}" for invoice in invalid_invoices)
            )
        else:
            console.print("Nothing to delete.")
        console.print()

        console.print(
            "[b u blue]Matching and linking Google Calendar events and invoices based "
            "on their start date.[/]"
        )
        matches, unmatched_events = self._link_by_start_date(merged_events)
        if matches:
            console.print("Matched and linked the following invoices and events:")
            console.print(
                "\n".join(
                    f"- [link={invoice.path.as_uri()}]{invoice.invoice_number}[/]: "
                    f"[link={event.link}]{event.link}[/]"
                    for invoice, event in matches
                )
            )
        else:
            console.print("Nothing to link.")
        console.print()

        console.print("[b u blue]Finding unlinked past events to bill them.[/]")
        unbilled_events = self._filter_unmatched_past_events(unmatched_events)
        if unbilled_events:
            if len(unbilled_events) == 1:
                unbilled_event = unbilled_events[0]
                console.print("Found one unbilled event:")
                console.print(unbilled_event)
                bill_now = Confirm.ask("Do you want to bill it now?")
                if bill_now:
                    self._bill_invoice(unbilled_event, console)
            console.print("Found unbilled past events:")
            columns = Columns(unbilled_events)
            console.print(columns)
        else:
            console.print("Nothing to bill.")

    def _bill_invoice(self, event: MergedEvent, console: Console) -> None:
        biller = Biller(self._paths, self._settings)
        invoice = biller.bill(event)
        invoice.write()
        console.print("Here is what the [r].yml[/] looks like:")
        console.print(
            Syntax(
                invoice.path.read_text(encoding="utf8"),
                "yaml",
                theme="default",
            )
        )
        if Confirm.ask("Do you want to edit it?"):
            launch(str(invoice.path), locate=True)
            Prompt.ask("Press enter when you are ready to continue")

    def _link_by_start_date(
        self, merged_events: Iterable[MergedEvent]
    ) -> Tuple[List[Tuple[Invoice, MergedEvent]], List[MergedEvent]]:
        matches = []
        event_starts = {
            min(merged_event.starts): merged_event for merged_event in merged_events
        }
        for invoice in self._unlinked_gcal_invoices:
            if invoice.gcal_info is None:
                event = event_starts.get(min(invoice.items[0].date.start))
                if event is not None:
                    matches.append((invoice, event))
                    with invoice.path.open(encoding="utf8") as fh:
                        data = safe_load(fh)
                        data["gcal_info"] = dict(event_id=event.id, link=event.link)
                    with NamedTemporaryFile(mode="w", encoding="utf8") as fh:
                        safe_dump(
                            data, fh, allow_unicode=True, default_flow_style=False
                        )
                        copy2(fh.name, invoice.path)
        matched_event_ids = set(event.id for _, event in matches)
        unmatched_events = [
            event for event in merged_events if event.id not in matched_event_ids
        ]
        return matches, unmatched_events

    def _delete_invalid_gcal_infos(
        self, merged_events: Iterable[MergedEvent]
    ) -> List[Invoice]:
        ids = {event.id for event in merged_events}
        invalid_invoices = []
        for invoice in self._linked_gcal_invoices:
            if invoice.gcal_info.event_id not in ids:
                with invoice.path.open(encoding="utf8") as fh:
                    data = safe_load(fh)
                    if "gcal_info" in data:
                        del data["gcal_info"]
                with NamedTemporaryFile(mode="w", encoding="utf8") as fh:
                    safe_dump(data, fh, allow_unicode=True, default_flow_style=False)
                    copy2(fh.name, invoice.path)
                invalid_invoices.append(invoice)
        return invalid_invoices

    def _filter_unmatched_past_events(
        self, merged_events: Iterable[MergedEvent]
    ) -> List[MergedEvent]:
        result = []
        today = date.today()
        linked_event_ids = set(
            invoice.gcal_info.event_id for invoice in self._linked_gcal_invoices
        )
        for event in (
            event for event in merged_events if event.id not in linked_event_ids
        ):
            end = max(
                start + duration
                for start, duration in zip(event.starts, event.durations)
            )
            if isinstance(end, date):
                end_date = end
            else:
                end_date = end.date()
            if end_date <= today and end_date >= self._settings.start_date:
                result.append(event)
        return result
