from database import HistoryStore


def test_history_store_isolates_users_and_persists_records(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    result = {"summary": {"total": 1, "errors": 1, "warnings": 0}, "issues": []}

    record = store.add("Ava", "example.py", "raise ValueError", result)

    assert record["filename"] == "example.py"
    assert len(store.list_for_user("Ava")) == 1
    assert store.list_for_user("Ben") == []

    reloaded = HistoryStore(tmp_path / "history.json")
    assert reloaded.list_for_user("Ava")[0]["id"] == record["id"]
    assert reloaded.learning_context("Ava")[0]["issues"] == []

    reloaded.delete_for_user("Ava")
    assert reloaded.list_for_user("Ava") == []