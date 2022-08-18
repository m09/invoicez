from datetime import date, timedelta
from logging import getLogger
from typing import List

from rich.prompt import Prompt
from yaml import safe_load

from invoicez.exceptions import InvoicezException
from invoicez.model import Invoice, Item, MergedEvent
from invoicez.paths import Paths
from invoicez.settings import Settings


class Biller:
    def __init__(self, paths: Paths, settings: Settings) -> None:
        self._paths = paths
        self._settings = settings
        self._logger = getLogger(__name__)

    def bill(self, merged_event: MergedEvent) -> Invoice:
        if merged_event.description:
            try:
                extra = safe_load(merged_event.description)
            except Exception:
                self._logger.warning(
                    f"Could not parse the description of event {merged_event} as yml."
                )
                extra = {}
        else:
            extra = {}

        invoice_number = self._get_next_invoice_number()
        training = self._settings.get_training(merged_event.training)
        description = self._settings.strings.invoice.description.format(
            training=training
        )
        company = merged_event.company
        if "ref" in extra:
            ref = extra["ref"]
        else:
            ref = Prompt.ask(
                "Enter the reference that we should mention on the invoice"
            )
        items = self._produce_main_items(merged_event)
        path = (
            self._paths.gcal_ymls_dir
            / self._settings.invoice_name_format_string.format(
                invoice_number=invoice_number,
                company=company,
                ref=ref,
                training=training,
            )
        ).with_suffix(".yml")
        return Invoice(
            path=path,
            invoice_number=invoice_number,
            description=description,
            company=company,
            ref=ref,
            date=date.today(),
            gcal_info=dict(link=merged_event.link, event_id=merged_event.id),
            items=items,
        )

    def _produce_main_items(self, merged_event: MergedEvent) -> List[Item]:
        training = self._settings.get_training(merged_event.training)
        rates = self._settings.get_training_rates(training.company, training.rates)

        whole_days: List[date] = []
        half_days: List[date] = []
        for start, duration in zip(merged_event.starts, merged_event.durations):
            if isinstance(start, date):
                if duration.seconds % 3600 * 24 != 0:
                    raise InvoicezException(
                        "When start is a date, duration should be in days."
                    )
                whole_days.extend(
                    start + timedelta(days=i) for i in range(duration.days)
                )
            else:
                if duration.seconds != 3600 * 3:
                    raise InvoicezException(
                        "When start is a datetime, the only duration supported is 3 "
                        "hours (half-day)."
                    )
                half_days.append(start.date())
        assert len(set(whole_days)) == len(
            whole_days
        ), f"{merged_event} has overlapping dates"
        assert len(set(half_days)) == len(
            half_days
        ), f"{merged_event} has overlapping dates"
        items = []
        if whole_days:
            items.append(
                Item(
                    date=whole_days,
                    n=len(whole_days),
                    description=self._settings.strings.invoice.training_day.format(
                        training=training
                    ),
                    unit_price=rates.training_day,
                )
            )
        if half_days:
            items.append(
                Item(
                    date=half_days,
                    n=len(half_days),
                    description=self._settings.strings.invoice.half_training_day.format(
                        training=training
                    ),
                    unit_price=rates.training_day // 2,
                ),
            )
        return items

    def _get_next_invoice_number(self) -> str:
        now = date.today()
        prefix = now.strftime("%Y-%m")
        n_invoices = 1
        for item in self._paths.git_dir.glob("**/*.yml"):
            with item.open(encoding="utf8") as fh:
                content = safe_load(fh)
            if "invoice_number" in content and content["invoice_number"].startswith(
                prefix
            ):
                n_invoices += 1
        return f"{now.strftime('%Y-%m')}-{n_invoices:03}"
