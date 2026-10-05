from analyzer import analyze_ast


def test_undefined_name_is_reported():
    issues = analyze_ast("print(missing_value)")
    assert any(issue["category"] == "NameError" for issue in issues)
