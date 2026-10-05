[app]
title = AI Bug Finder
package.name = aibugfinder
package.domain = org.shreya
source.dir = .
source.include_exts = py,json,kv
source.include_patterns = main.py,mobile_app.py,auth_manager.py,analyzer/*.py,database/*.py,database/*.json,engine/*.py
source.exclude_dirs = .git,.venv,.venv-1,.venv-mobile,.buildozer,__pycache__,.pytest_cache,tests,test_cases,reports,streamlit,bin,dist,build
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

android.permissions =
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
