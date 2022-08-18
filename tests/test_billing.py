from datetime import date, timedelta
from pathlib import Path

from pytest import fixture

from invoicez.billing import Biller
from invoicez.model import MergedEvent
from invoicez.paths import Paths
from invoicez.settings import Settings


@fixture
def biller() -> Biller:
    paths = Paths(Path.cwd())
    return Biller(paths, Settings.load(paths))


def test_billing(biller: Biller) -> None:
    today = date.today()
    one_day = timedelta(days=1)
    invoice = biller.bill(
        MergedEvent(
            company="company1",
            training="training11",
            place="1",
            description="ref: REF1",
            link="link_1",
            id="id_1",
            starts=[date.today()],
            durations=[timedelta(days=4)],
        )
    )
    assert len(invoice.items) == 1
    assert invoice.items[0].n == 4
    assert invoice.items[0].unit_price == 750
    assert invoice.items[0].description == "Day of “Training 1” training"
    assert invoice.items[0].date.start == [today + one_day * i for i in range(4)]
    assert invoice.ref == "REF1"
    assert invoice.description == "Invoice for the “Training 1” training session"


def test_billing_default_rates(biller: Biller) -> None:
    today = date.today()
    one_day = timedelta(days=1)
    invoice = biller.bill(
        MergedEvent(
            company="company2",
            training="training21",
            place="1",
            description="ref: REF1",
            link="link_1",
            id="id_1",
            starts=[date.today()],
            durations=[timedelta(days=4)],
        )
    )
    assert len(invoice.items) == 1
    assert invoice.items[0].n == 4
    assert invoice.items[0].unit_price == 800
    assert invoice.items[0].description == "Day of “Training 1” training"
    assert invoice.items[0].date.start == [today + one_day * i for i in range(4)]
    assert invoice.ref == "REF1"
    assert invoice.description == "Invoice for the “Training 1” training session"
