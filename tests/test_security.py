from analyzer import analyze_security
from engine import detect_bugs


def test_eval_is_flagged():
    assert analyze_security("eval(user_input)")[0]["category"] == "Security"


def test_security_findings_skip_runtime_execution():
    result = detect_bugs("eval('1 + 1')", run_code=True)
    assert all(issue["category"] == "Security" for issue in result["issues"])
