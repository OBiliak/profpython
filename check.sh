#!/bin/sh
# CI-ready check: static type checking and the whole pytest suite with the coverage threshold.
# Run from the project root: sh check.sh (exit code is not 0 if any step fails).
set -e
echo "== mypy =="
python -m mypy
echo "== pytest + coverage (fail_under = 80) =="
python -m pytest --cov --cov-report=term-missing
echo "== OK: перевірку пройдено =="
