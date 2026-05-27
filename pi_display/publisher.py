from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pi_display.models import build_event_id

SOURCE_URL = "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    event = dict(raw)
    event["id"] = raw.get("id") or build_event_id(raw)
    event["meta"] = list(raw.get("meta") or [])
    event["isClass"] = bool(raw.get("isClass"))
    return event


def build_slides(
    events: list[dict[str, Any]],
    videos: dict[str, dict[str, Any]],
    associations: dict[str, str],
) -> list[dict[str, Any]]:
    slides: list[dict[str, Any]] = []
    for raw_event in events:
        event = normalize_event(raw_event)
        video_id = associations.get(event["id"])
        video = videos.get(video_id)

        if video and video.get("enabled", True):
            slides.append(
                {
                    "type": "video",
                    "id": video["id"],
                    "eventId": event["id"],
                    "title": video.get("title") or "Promo video",
                    "src": video["storage_path"] if "storage_path" in video else video["src"],
                    "poster": video.get("poster_path") or video.get("poster"),
                    "durationSeconds": video.get("duration_seconds")
                    or video.get("durationSeconds")
                    or 20,
                }
            )

        slides.append(
            {
                "type": "event",
                "id": event["id"],
                "eventId": event["id"],
                "title": event.get("title") or "Untitled event",
                "category": event.get("category"),
                "dateText": event.get("dateText"),
                "startTime": event.get("startTime"),
                "cost": event.get("cost"),
                "status": event.get("status"),
                "meta": event.get("meta", []),
                "link": event.get("link"),
                "imageLocal": event.get("imageLocal"),
                "qrLocal": event.get("qrLocal"),
                "isClass": bool(event.get("isClass")),
            }
        )

    return slides


def build_output_payloads(
    events: list[dict[str, Any]],
    videos: dict[str, dict[str, Any]],
    associations: dict[str, str],
    include_classes: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_events = [normalize_event(item) for item in events]
    slides = build_slides(normalized_events, videos, associations)
    fetched_at = datetime.now(timezone.utc).isoformat()
    return (
        {
            "fetchedAt": fetched_at,
            "includeClasses": include_classes,
            "sourceUrl": SOURCE_URL,
            "total": len(normalized_events),
            "items": normalized_events,
            "lastError": None,
        },
        {
            "fetchedAt": fetched_at,
            "total": len(slides),
            "slides": slides,
        },
    )
