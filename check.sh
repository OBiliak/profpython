#!/bin/sh
# The same checks as the GitHub Actions job quality-and-tests, run locally from the project root:
# sh check.sh (exit code is not 0 if any step fails).
set -e
echo "== ruff check =="
python -m ruff check .
echo "== ruff format --check =="
python -m ruff format --check .
echo "== mypy =="
python -m mypy
echo "== pytest + coverage (fail_under = 80) =="
python -m pytest --cov --cov-report=term-missing
echo "== OK: перевірку пройдено =="
