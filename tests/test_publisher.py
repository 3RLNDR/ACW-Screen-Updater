from pi_display.publisher import build_output_payloads, build_slides


def test_build_slides_places_video_before_paired_event():
    events = [
        {
            "id": "event-jazz-night-2026-06-01",
            "title": "Jazz Night",
            "category": "Music",
            "dateText": "01 Jun 2026",
            "startTime": "7pm",
            "cost": "GBP14",
            "link": "https://example.com/jazz-night",
            "imageLocal": "./cache/images/jazz-night.jpg",
            "qrLocal": "./cache/qr/jazz-night.png",
            "meta": ["Live in the auditorium"],
            "status": "",
            "isClass": False,
        }
    ]
    videos = {
        "video-jazz-trailer": {
            "id": "video-jazz-trailer",
            "title": "Jazz Night Trailer",
            "src": "./cache/videos/jazz-night.mp4",
            "poster": None,
            "durationSeconds": 20,
            "enabled": True,
        }
    }
    associations = {"event-jazz-night-2026-06-01": "video-jazz-trailer"}

    slides = build_slides(events, videos, associations)

    assert [slide["type"] for slide in slides] == ["video", "event"]
    assert slides[0]["eventId"] == "event-jazz-night-2026-06-01"
    assert slides[1]["id"] == "event-jazz-night-2026-06-01"


def test_build_output_payloads_writes_events_and_slides():
    events = [
        {
            "title": "Jazz Night",
            "category": "Music",
            "dateText": "01 Jun 2026",
            "startTime": "7pm",
        }
    ]

    events_payload, slides_payload = build_output_payloads(
        events,
        videos={},
        associations={},
        include_classes=False,
    )

    assert events_payload["includeClasses"] is False
    assert events_payload["items"][0]["id"].startswith("event-jazz-night")
    assert slides_payload["slides"][0]["type"] == "event"
