"""Structured logging shared across every module (feature 6: production readiness)."""
import sys
from loguru import logger
from config.settings import settings

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    backtrace=False,
    diagnose=False,
)
logger.add(
    "logs/app.log",
    rotation="20 MB",
    retention="14 days",
    level="DEBUG",
    enqueue=True,
)

__all__ = ["logger"]
