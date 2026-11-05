#!/bin/sh
# CI-like check: static type checking and unit tests. Run from the project root: sh check.sh
set -e
echo "== mypy =="
python -m mypy
echo "== unittest =="
python -m unittest discover -s tests
echo "== OK: перевірку пройдено =="
