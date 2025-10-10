import logging
import json
from datetime import datetime
from typing import Any, Dict


class StructuredLogger:
    def __init__(self, name: str, level: str = "INFO", format_type: str = "json"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.format_type = format_type

        handler = logging.StreamHandler()
        if format_type == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))

        self.logger.handlers = []
        self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **metadata):
        log_func = getattr(self.logger, level)
        if self.format_type == "json":
            log_func(message, extra={"metadata": metadata})
        else:
            if metadata:
                log_func(f"{message} | {metadata}")
            else:
                log_func(message)

    def debug(self, message: str, **metadata):
        self._log("debug", message, **metadata)

    def info(self, message: str, **metadata):
        self._log("info", message, **metadata)

    def warning(self, message: str, **metadata):
        self._log("warning", message, **metadata)

    def error(self, message: str, **metadata):
        self._log("error", message, **metadata)

    def critical(self, message: str, **metadata):
        self._log("critical", message, **metadata)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "metadata"):
            log_data.update(record.metadata)

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str, level: str = "INFO", format_type: str = "json") -> StructuredLogger:
    return StructuredLogger(name, level, format_type)
