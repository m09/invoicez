from .conftest import FakeSyncer


def test_list_events(syncer: FakeSyncer) -> None:
    assert syncer.list_events()
