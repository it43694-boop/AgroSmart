import logging
import os
from typing import Any, Dict


class StructuredLogger:
    """Logger simple et structuré pour les événements métier."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    def info(self, event: str, **context: Any) -> None:
        self.logger.info("%s %s", event, self._serialize(context))

    def warning(self, event: str, **context: Any) -> None:
        self.logger.warning("%s %s", event, self._serialize(context))

    def error(self, event: str, **context: Any) -> None:
        self.logger.error("%s %s", event, self._serialize(context))

    def _serialize(self, context: Dict[str, Any]) -> str:
        return str(context)


logger = StructuredLogger("agrosmart")
