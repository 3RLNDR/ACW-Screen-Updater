import json
import shutil
import uuid
from io import BytesIO
from pathlib import Path

from pi_display.publisher import build_output_payloads
from pi_display.web import create_app, parse_multipart_files


def test_parse_multipart_files_extracts_uploaded_video_payload():
    boundary = "test-boundary"
    video_bytes = b"\x00fake mp4 bytes\r\nwith a newline"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="file"; filename="trailer.mp4"\r\n',
            b"Content-Type: video/mp4\r\n\r\n",
            video_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )

    files = parse_multipart_files(body, f"multipart/form-data; boundary={boundary}")

    assert files["file"] == {
        "filename": "trailer.mp4",
        "content_type": "video/mp4",
        "data": video_bytes,
    }


def test_video_upload_and_association_flow():
    root_dir = Path.cwd() / ".tmp" / f"web-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        public_dir = root_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        (public_dir / "index.html").write_text(
            "<!doctype html><title>ACW</title>", encoding="utf-8"
        )

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
        (public_dir / "events.json").write_text(
            json.dumps(events_payload), encoding="utf-8"
        )
        (public_dir / "slides.json").write_text(
            json.dumps(slides_payload), encoding="utf-8"
        )

        app = create_app(root_dir)
        client = app.test_client()

        upload_response = client.post(
            "/api/videos",
            files={"file": ("jazz-night.mp4", BytesIO(b"fake mp4 bytes"), "video/mp4")},
        )
        assert upload_response.status_code == 201
        assert upload_response.json()["slidesUpdated"] is True
        video_id = upload_response.json()["video"]["id"]

        association_response = client.put(
            "/api/video-associations/event-jazz-night-2026-06-01",
            json={"videoId": video_id},
        )
        assert association_response.status_code == 200
        assert association_response.json()["eventId"] == "event-jazz-night-2026-06-01"
        assert association_response.json()["slidesUpdated"] is True

        slides_response = client.get("/api/slides")
        assert slides_response.status_code == 200
        assert [slide["type"] for slide in slides_response.json()["slides"]] == [
            "video",
            "event",
        ]
        assert (
            slides_response.json()["slides"][0]["eventId"]
            == "event-jazz-night-2026-06-01"
        )
        assert slides_response.json()["slides"][0]["src"].startswith(
            "./cache/videos/jazz-night-"
        )
        written_slides = json.loads(
            (public_dir / "slides.json").read_text(encoding="utf-8")
        )
        assert [slide["type"] for slide in written_slides["slides"]] == [
            "video",
            "event",
        ]

        videos_response = client.get("/api/videos")
        assert videos_response.status_code == 200
        assert videos_response.json()["items"][0]["id"] == video_id

        associations_response = client.get("/api/video-associations")
        assert (
            associations_response.json()["items"]["event-jazz-night-2026-06-01"]
            == video_id
        )

        clear_response = client.delete(
            "/api/video-associations/event-jazz-night-2026-06-01"
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["slidesUpdated"] is True

        cleared_slides_response = client.get("/api/slides")
        assert [
            slide["type"] for slide in cleared_slides_response.json()["slides"]
        ] == ["event"]
        cleared_written_slides = json.loads(
            (public_dir / "slides.json").read_text(encoding="utf-8")
        )
        assert [slide["type"] for slide in cleared_written_slides["slides"]] == [
            "event"
        ]
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)
