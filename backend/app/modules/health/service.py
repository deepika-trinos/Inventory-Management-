"""Health check logic."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def is_database_reachable(db: Session) -> bool:
    """Run the smallest possible query. True if PostgreSQL answers."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        # Log the real reason on the server; never send it to the browser.
        logger.exception("Database health check failed")
        return False
