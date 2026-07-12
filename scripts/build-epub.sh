#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src .venv/bin/python scripts/build_publications.py --format epub
