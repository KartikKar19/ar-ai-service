import logging
import sys
from app.core.config import settings

def configure_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='{"level":"%(levelname)s","ts":"%(asctime)s","logger":"ai-service","msg":"%(message)s"}',
        handlers=[logging.StreamHandler(sys.stdout)],
    )