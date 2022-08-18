from .conftest import FakeCalendar


def test_list_events(calendar: FakeCalendar) -> None:
    assert calendar.list_events()
