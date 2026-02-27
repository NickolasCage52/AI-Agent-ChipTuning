from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger("parts_events")


def log_event(event_type: str, data: dict) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        **data,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
