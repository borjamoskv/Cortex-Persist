# [C5-REAL] Exergy-Maximized
"""
Sovereign JSONL Logging Formatter.

Implements a deterministic JSON Lines (JSONL) serialization format for system logs,
making them immediately parseable by jq, grep, or any log aggregation system.
"""

import json
import logging
import time

class JsonlFormatter(logging.Formatter):
    """Formats log records as flat, single-line JSON objects."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Construct the core deterministic log structure
        log_obj = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Merge in any extra fields passed via extra={...}
        # Python's LogRecord attributes to ignore
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName", "message"
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                log_obj[key] = str(value)  # Cast to string to ensure JSON serialization

        return json.dumps(log_obj)

def setup_cortex_logging(jsonl: bool = True, level: int = logging.INFO) -> None:
    """
    Centralized logging bootstrapper.
    Overwrites the root logger configuration.
    """
    # Remove all existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if jsonl:
        handler.setFormatter(JsonlFormatter())
    else:
        # Fallback for explicit non-jsonl paths if ever needed, though JSONL is the default
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    root_logger.addHandler(handler)
    root_logger.setLevel(level)
