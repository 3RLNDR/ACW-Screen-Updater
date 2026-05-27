import json
import shutil
import uuid
from io import BytesIO
from pathlib import Path

from pi_display.publisher import build_output_payloads
from pi_display.web import create_app


def test_video_upload_and_association_flow():
    root_dir = Path.cwd() / ".tmp" / f"web-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        public_dir = root_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        (public_dir / "index.html").write_text("<!doctype html><title>ACW</title>", encoding="utf-8")

        events_payload, slides_payload = build_output_payloads(
            [
                {
                    "id": "event-jazz-night-2026-06-01",
                    "title": "Jazz Night",
                    "category": "Music",
                    "dateText": "01 Jun 2026",
                }
            ],
            videos={},
            associations={},
            include_classes=False,
        )
        (public_dir / "events.json").write_text(json.dumps(events_payload), encoding="utf-8")
        (public_dir / "slides.json").write_text(json.dumps(slides_payload), encoding="utf-8")

        app = create_app(root_dir)
        client = app.test_client()

        upload_response = client.post(
            "/api/videos",
            files={"file": ("jazz-night.mp4", BytesIO(b"fake mp4 bytes"), "video/mp4")},
        )
        assert upload_response.status_code == 201
        video_id = upload_response.json()["video"]["id"]

        association_response = client.put(
            "/api/video-associations/event-jazz-night-2026-06-01",
            json={"videoId": video_id},
        )
        assert association_response.status_code == 200
        assert association_response.json()["eventId"] == "event-jazz-night-2026-06-01"

        videos_response = client.get("/api/videos")
        assert videos_response.status_code == 200
        assert videos_response.json()["items"][0]["id"] == video_id

        associations_response = client.get("/api/video-associations")
        assert associations_response.json()["items"]["event-jazz-night-2026-06-01"] == video_id
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)
