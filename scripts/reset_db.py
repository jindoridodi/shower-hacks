#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.errors import ResetRefused
from apps.api.reset import reset_local_database


def main() -> None:
    try:
        path = reset_local_database()
    except ResetRefused as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Reset local development database at {path}")


if __name__ == "__main__":
    main()
