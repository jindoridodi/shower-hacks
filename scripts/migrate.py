#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.config import get_settings
from apps.api.db import apply_migrations


def main() -> None:
    path = get_settings().database_path
    applied = apply_migrations(path)
    if applied:
        print("Applied: " + ", ".join(applied))
    else:
        print("Migrations already current")
    print(f"Database: {path}")


if __name__ == "__main__":
    main()
