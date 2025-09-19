import logging
import sys
from app.core.config import settings

class ChromaTelemetryFilter(logging.Filter):
    """Filter out ChromaDB telemetry errors"""
    def filter(self, record):
        # Filter out telemetry capture() errors
        message = record.getMessage()
        if "capture() takes 1 positional argument but 3 were given" in message:
            return False
        if "Failed to send telemetry event" in message:
            return False
        return True

def configure_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='{"level":"%(levelname)s","ts":"%(asctime)s","logger":"ai-service","msg":"%(message)s"}',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Add telemetry filter to suppress ChromaDB telemetry errors
    telemetry_filter = ChromaTelemetryFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(telemetry_filter)