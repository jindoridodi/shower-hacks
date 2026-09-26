#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.config import get_settings
from apps.api.db import apply_migrations, make_engine, make_session_factory
from apps.api.seed import seed_demo


def main() -> None:
    path = get_settings().database_path
    apply_migrations(path)
    engine = make_engine(path)
    session = make_session_factory(engine)()
    try:
        result = seed_demo(session)
    finally:
        session.close()
        engine.dispose()
    print(f"project_id={result.project.id}")
    print(f"source_id={result.source.id}")
    print(f"canonical_url={result.source.canonical_url}")
    print("created=yes" if result.created else "created=no")


if __name__ == "__main__":
    main()
