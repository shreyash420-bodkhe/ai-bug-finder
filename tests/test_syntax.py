from analyzer import check_syntax


def test_invalid_syntax_is_reported():
    assert check_syntax("def broken(\n") [0]["category"] == "SyntaxError"
