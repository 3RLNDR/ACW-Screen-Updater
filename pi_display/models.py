from __future__ import annotations

import hashlib
import re
from typing import Any


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return normalized or "event"


def build_event_id(item: dict[str, Any]) -> str:
    stable_bits = [
        str(item.get("title", "")),
        str(item.get("category", "")),
        str(item.get("dateText", "")),
        str(item.get("startTime", "")),
    ]
    digest = hashlib.sha1("|".join(stable_bits).encode("utf-8")).hexdigest()[:8]
    return f"event-{slugify(str(item.get('title', 'event')))}-{digest}"
