"""Run queued, allowlisted crawl jobs.

Usage:
    python -m workers.crawl_worker --once

The worker deliberately performs one job per invocation by default. A process
manager can run it repeatedly, while local development and tests can safely use
``run_once`` without a broker dependency.
"""

from __future__ import annotations

import argparse
import logging

from apps.api.config import get_settings
from apps.api.db import apply_migrations, make_engine, make_session_factory
from apps.api.services.crawls import claim_next_queued_crawl, run_claimed_crawl

LOGGER = logging.getLogger(__name__)


def run_once() -> str | None:
    """Claim and process one queued job, returning its ID when work was found."""

    settings = get_settings()
    apply_migrations(settings.database_path)
    engine = make_engine(settings.database_path)
    session = make_session_factory(engine)()
    try:
        job = claim_next_queued_crawl(session)
        if job is None:
            return None
        try:
            run_claimed_crawl(session, job.id)
        except Exception:
            # The service stores a safe terminal failure before re-raising. Do
            # not log source content, request headers, or credentials here.
            LOGGER.exception("crawl job failed", extra={"crawl_id": job.id})
        return job.id
    finally:
        session.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one approved crawl job.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job (default).")
    parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    job_id = run_once()
    if job_id:
        LOGGER.info("processed crawl job", extra={"crawl_id": job_id})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
