from engine import analyze_project_folder, detect_bugs


def test_detector_matches_type_error():
    result = detect_bugs('total = "10" + 5', run_code=True)
    assert result["summary"]["errors"] == 1
    assert result["issues"][0]["rule"] == "literal-type-error"
    assert result["fixed_code"] == 'total = str("10") + str(5)'


def test_literal_type_error_has_fix_without_running_user_code():
    result = detect_bugs('total = "10" + 5', run_code=False)

    assert result["summary"]["errors"] == 1
    assert result["issues"][0]["rule"] == "literal-type-error"
    assert result["fixed_code"] == 'total = str("10") + str(5)'


def test_literal_type_error_fix_supports_number_on_left():
    result = detect_bugs('total = 5 + "10"', run_code=False)

    assert result["summary"]["errors"] == 1
    assert result["fixed_code"] == 'total = str(5) + str("10")'


def test_project_folder_analysis_fixes_python_files(tmp_path):
    src_dir = tmp_path / "demo_project"
    src_dir.mkdir()
    (src_dir / "app.py").write_text('total = "10" + 5\n', encoding='utf-8')
    (src_dir / "helper.py").write_text('def greet(name):\n    return "hi" + name\n', encoding='utf-8')

    result = analyze_project_folder(src_dir, run_code=True)

    assert result["files_analyzed"] >= 2
    assert result["summary"]["total"] >= 1
    assert (src_dir / "app.py").read_text(encoding='utf-8') == 'total = str("10") + str(5)\n'
