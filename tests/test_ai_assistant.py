import json
from io import BytesIO

from engine.ai_assistant import _validated_fixed_code, analyze_with_ai
from engine import detect_bugs


def test_assistant_rejects_syntax_invalid_proposed_fix():
    assert _validated_fixed_code("def fixed():\n    return 1") == "def fixed():\n    return 1"
    assert _validated_fixed_code("def broken(:") is None


def test_assistant_falls_back_to_local_findings_without_api_key():
    local_result = {
        "issues": [{"title": "Possible undefined name", "line": 1}],
        "summary": {"total": 1},
        "fixed_code": "print(known_value)",
    }

    result = analyze_with_ai(
        "print(missing_value)",
        "example.py",
        "Fix the undefined name",
        local_result,
        api_key="",
    )

    assert result["source"] == "local analyzer"
    assert result["issues"] == local_result["issues"]
    assert result["fixed_code"] == local_result["fixed_code"]


def test_pasted_syntax_error_gets_valid_corrected_code():
    result = analyze_with_ai(
        "def greet(name)\n    return name",
        "pasted_code.py",
        "Find and fix the error.",
        detect_bugs("def greet(name)\n    return name", run_code=False),
        api_key="",
    )

    assert result["fixed_code"] == "def greet(name):\n    return name"
    assert "cannot understand" in result["issues"][0]["message"]


def test_queue_infinite_loop_gets_bounded_correction():
    source = 'queue = ["job-101"]\n\nwhile True:\n    current_job = queue.pop(0)\n    print(current_job)\n'
    result = analyze_with_ai(
        source,
        "pasted_code.py",
        "Find and fix the error.",
        detect_bugs(source, run_code=False),
        api_key="",
    )

    assert "while queue:" in result["fixed_code"]


def test_ai_issue_line_numbers_are_one_based_and_within_source(monkeypatch):
    source = "value = 1\nprint(value)\n"
    model_result = {
        "explanation": "A variable is printed.",
        "issues": [
            {"title": "First issue", "message": "Details", "solution": "Fix it", "line": "2", "severity": "error"},
            {"title": "Unknown location", "message": "Details", "solution": "Review it", "line": 12, "severity": "warning"},
        ],
        "fixed_code": None,
    }
    payload = {"choices": [{"message": {"content": json.dumps(model_result)}}]}

    def fake_urlopen(request, timeout):
        prompt = json.loads(request.data)["messages"][1]["content"]
        assert json.loads(prompt)["source_lines"] == [
            {"line": 1, "code": "value = 1"},
            {"line": 2, "code": "print(value)"},
        ]
        return BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("engine.ai_assistant.urlopen", fake_urlopen)
    result = analyze_with_ai(
        source,
        "pasted-code.py",
        "Find bugs and fixes.",
        {"issues": [], "summary": {"total": 0, "errors": 0, "warnings": 0}, "fixed_code": None},
        api_key="test-key",
    )

    assert result["issues"][0]["line"] == 2
    assert result["issues"][1]["line"] is None