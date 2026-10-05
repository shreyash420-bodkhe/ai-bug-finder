import builtins

from database import BugDatabase, HistoryStore
from engine import detect_bugs


def test_database_loads_catalog():
    bugs = BugDatabase().load()
    assert bugs and bugs[0]["id"]


def test_database_has_solution_for_every_catalog_entry():
    database = BugDatabase()
    solutions = database.solutions()

    for bug in database.load():
        assert bug["solution"]
        assert bug["category"] in solutions or bug["category"] == "Security"


def test_database_covers_builtin_exception_types():
    catalog_categories = {item["category"] for item in BugDatabase().load()}
    builtin_exceptions = {
        name
        for name, value in vars(builtins).items()
        if not name.startswith("_")
        and isinstance(value, type)
        and issubclass(value, BaseException)
        and value.__name__ == name
    }

    assert builtin_exceptions <= catalog_categories


def test_logic_and_timeout_find_database_entries():
    database = BugDatabase()

    logic = database.find_matches("Possible infinite loop")
    timeout = database.find_matches("Execution exceeded the smoke-test limit")

    assert any(item["id"] == "L001" for item in logic)
    assert any(item["id"] == "E053" for item in timeout)


def test_database_loads_safe_fix_catalog():
    fixes = BugDatabase().fixes()
    assert fixes["infinite-loop"]["safe"] is True
    assert fixes["identity-comparison"]["safe"] is True


def test_database_exposes_code_solutions():
    database = BugDatabase()
    code_solutions = database.code_solutions()

    assert "TypeError" in code_solutions
    assert "NameError" in code_solutions
    assert "print(" in code_solutions["TypeError"] or "str(" in code_solutions["TypeError"]


def test_detected_bug_returns_code_example():
    result = BugDatabase().code_solutions().get("TypeError")
    assert result is not None
    assert "str(" in result or "int(" in result


def test_history_store_lists_records_for_admin(tmp_path):
    history = HistoryStore(tmp_path / "history.db")
    first_user_record = history.add(
        "person@example.com",
        "uploaded_project",
        "# File: app.py\nprint('hello')",
        {"summary": {"total": 0}, "issues": [], "fixed_code": None},
    )
    second_user_record = history.add(
        "other@example.com",
        "main.py",
        "print('other')",
        {"summary": {"total": 0}, "issues": [], "fixed_code": None},
    )

    assert history.list_for_user("person@example.com") == [first_user_record]
    assert history.list_for_user("other@example.com") == [second_user_record]
    all_records = history.list_all()
    assert all_records == [first_user_record, second_user_record]
    assert [record["user"] for record in all_records] == [
        "person@example.com",
        "other@example.com",
    ]


def test_pasted_code_analysis_saves_error_suggestion_and_fix(tmp_path):
    source = 'total = "10" + 5'
    result = detect_bugs(source, run_code=True)
    history = HistoryStore(tmp_path / "history.db")
    history.add("person@example.com", "pasted-code", source, result)

    saved = history.list_for_user("person@example.com")[0]
    type_error = next(
        issue for issue in saved["result"]["issues"]
        if issue.get("category") == "TypeError"
    )

    assert saved["result"]["summary"]["errors"] >= 1
    assert type_error["message"]
    assert type_error["solution"]
    assert saved["result"]["fixed_code"] == 'total = str("10") + str(5)'
