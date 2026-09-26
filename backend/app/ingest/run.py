"""Cron entry point: python -m app.ingest.run [--source all] [--company slug ...]

Designed for Render Cron Job / system cron. Exit code 0 on success, 1 if any errors.
"""
from __future__ import annotations

import sys

from app.ingest.cli import main

if __name__ == "__main__":
    # Default: all sources, all companies — extra flags passthrough
    argv = sys.argv[1:]
    if not any(a.startswith("--source") for a in argv):
        argv = ["--source", "all", *argv]
    raise SystemExit(main(argv))
