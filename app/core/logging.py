"""Loguru configuration shared by bot, web and scheduler processes."""
from __future__ import annotations

import sys

from loguru import logger

from app.core.config import get_settings


def setup_logging(component: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=get_settings().log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            f"<cyan>{component}</cyan> | {{name}}:{{function}}:{{line}} - {{message}}"
        ),
    )
    logger.add(
        f"logs/{component}.log",
        level=get_settings().log_level,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
    )
