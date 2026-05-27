# Pi Video Slideshow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-platform the display to a Raspberry Pi-hosted hybrid publisher and add locally hosted video slides that can be associated with specific events through the dashboard UI.

**Architecture:** Add a small Python Flask service on the Pi that scrapes and publishes `public/events.json` plus `public/slides.json`, persists video assets and event associations in SQLite, and serves the existing static frontend plus new admin endpoints. Keep the browser frontend mostly static, but update the dashboard and fullscreen player to consume generated slide data and support a new `video` slide type that plays immediately before its paired event slide.

**Tech Stack:** Python 3, Flask, sqlite3, requests, BeautifulSoup 4, pytest, plain HTML/CSS/JavaScript

---

## File Structure

- Create: `pi_display/__init__.py`
- Create: `pi_display/config.py`
- Create: `pi_display/database.py`
- Create: `pi_display/models.py`
- Create: `pi_display/scraper.py`
- Create: `pi_display/publisher.py`
- Create: `pi_display/web.py`
- Create: `pi_display/refresh.py`
- Create: `public/video-admin-model.js`
- Create: `public/slide-sequence.js`
- Create: `tests/test_scraper.py`
- Create: `tests/test_publisher.py`
- Create: `tests/test_database.py`
- Create: `tests/test_web.py`
- Create: `tests/app-view-model.test.mjs`
- Create: `tests/fullscreen-slides.test.mjs`
- Create: `requirements.txt`
- Create: `systemd/acw-display.service`
- Create: `systemd/acw-refresh.service`
- Create: `systemd/acw-refresh.timer`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `public/index.html`
- Modify: `public/app.js`
- Modify: `public/fullscreen.html`
- Modify: `public/fullscreen.js`
- Modify: `public/styles.css`

### Responsibility Map

- `pi_display/config.py`: runtime paths and environment-backed configuration
- `pi_display/database.py`: SQLite connection, schema setup, and row helpers
- `pi_display/models.py`: event, video, association, and slide normalization helpers
- `pi_display/scraper.py`: Pi-native event scraping and asset caching
- `pi_display/publisher.py`: build `events.json` and `slides.json` from scraped events plus associations
- `pi_display/web.py`: Flask app, static serving, upload API, association API, and refresh endpoint
- `pi_display/refresh.py`: scheduled refresh entrypoint for cron/systemd
- `public/video-admin-model.js`: pure helpers for dashboard association view models
- `public/slide-sequence.js`: pure helpers for fullscreen slide sequencing
- `public/app.js`: existing dashboard data loading plus new event/video association UI
- `public/fullscreen.js`: mixed `video` and `event` slide playback
- `public/fullscreen.html`: add the dedicated promo video element
- `public/styles.css`: admin panel and fullscreen video-state styling

### Delivery Notes

- Keep `public/events.json` as the event payload the dashboard already understands.
- Add `public/slides.json` as the generated source for the fullscreen rotation.
- Store uploaded video files under `public/cache/videos/` so the browser can play them as static assets.
- Store the SQLite database under `data/acw-display.sqlite3` and ignore it in git.

### Task 1: Bootstrap The Pi Runtime

**Files:**
- Create: `requirements.txt`
- Create: `pi_display/__init__.py`
- Create: `pi_display/config.py`
- Modify: `.gitignore`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing configuration test**

```python
from pathlib import Path

from pi_display.config import AppConfig


def test_default_runtime_paths_live_inside_repo(tmp_path: Path):
    config = AppConfig.from_root(tmp_path)

    assert config.public_dir == tmp_path / "public"
    assert config.video_dir == tmp_path / "public" / "cache" / "videos"
    assert config.database_path == tmp_path / "data" / "acw-display.sqlite3"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_database.py::test_default_runtime_paths_live_inside_repo -q`
Expected: `ModuleNotFoundError: No module named 'pi_display'`

- [ ] **Step 3: Add the minimal package bootstrap and configuration**

```python
# pi_display/__init__.py
__all__ = ["config", "database", "models", "publisher", "refresh", "scraper", "web"]
```

```python
# pi_display/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    public_dir: Path
    video_dir: Path
    image_dir: Path
    qr_dir: Path
    database_path: Path

    @classmethod
    def from_root(cls, root_dir: Path) -> "AppConfig":
        public_dir = root_dir / "public"
        return cls(
            root_dir=root_dir,
            public_dir=public_dir,
            video_dir=public_dir / "cache" / "videos",
            image_dir=public_dir / "cache" / "images",
            qr_dir=public_dir / "cache" / "qr",
            database_path=root_dir / "data" / "acw-display.sqlite3",
        )
```

```text
# requirements.txt
beautifulsoup4==4.13.4
Flask==3.1.1
pytest==8.4.1
requests==2.32.3
```

```gitignore
cache/
public/cache/images/
public/cache/videos/
backup-local-server/cache/
server.log
.DS_Store
Thumbs.db
gitdata/
.gitdata/
.git-broken*/
data/
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_database.py::test_default_runtime_paths_live_inside_repo -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore pi_display/__init__.py pi_display/config.py tests/test_database.py
git commit -m "feat: scaffold pi display runtime"
```

### Task 2: Port Event Scraping And Slide Publishing

**Files:**
- Create: `pi_display/models.py`
- Create: `pi_display/scraper.py`
- Create: `pi_display/publisher.py`
- Create: `tests/test_scraper.py`
- Create: `tests/test_publisher.py`

- [ ] **Step 1: Write the failing publisher test for `video -> event` ordering**

```python
from pi_display.publisher import build_slides


def test_build_slides_places_video_before_paired_event():
    events = [
        {
            "id": "event-jazz-night-2026-06-01",
            "title": "Jazz Night",
            "category": "Music",
            "dateText": "01 Jun 2026",
            "startTime": "7pm",
            "cost": "£14",
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_publisher.py::test_build_slides_places_video_before_paired_event -q`
Expected: `ImportError` for `pi_display.publisher`

- [ ] **Step 3: Implement the event model, stable IDs, scraper shell, and slide builder**

```python
# pi_display/models.py
from __future__ import annotations

import hashlib
import re
from typing import Any


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "event"


def build_event_id(item: dict[str, Any]) -> str:
    stable_bits = [
        item.get("title", ""),
        item.get("category", ""),
        item.get("dateText", ""),
        item.get("startTime", ""),
    ]
    digest = hashlib.sha1("|".join(stable_bits).encode("utf-8")).hexdigest()[:8]
    return f"event-{slugify(item.get('title', 'event'))}-{digest}"
```

```python
# pi_display/publisher.py
from __future__ import annotations

from typing import Any

from pi_display.models import build_event_id


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    event = dict(raw)
    event["id"] = raw.get("id") or build_event_id(raw)
    event["meta"] = list(raw.get("meta") or [])
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
                    "title": video["title"],
                    "src": video["src"],
                    "poster": video.get("poster"),
                    "durationSeconds": video.get("durationSeconds") or 20,
                }
            )

        slides.append(
            {
                "type": "event",
                "id": event["id"],
                "eventId": event["id"],
                "title": event["title"],
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
```

```python
# pi_display/scraper.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def scrape_events(config, include_classes: bool) -> list[dict[str, Any]]:
    source_path = config.public_dir / "events.json"
    if not source_path.exists():
        return []
    items = json.loads(source_path.read_text(encoding="utf-8")).get("items", [])
    if include_classes:
        return items
    return [item for item in items if not item.get("isClass")]


def scrape_events_from_fixture(source_path: Path) -> list[dict[str, Any]]:
    return json.loads(source_path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Add a red-green test for writing `events.json` and `slides.json`**

```python
import json

from pi_display.publisher import build_output_payloads


def test_build_output_payloads_writes_events_and_slides(tmp_path):
    events = [{"title": "Jazz Night", "category": "Music", "dateText": "01 Jun 2026", "startTime": "7pm"}]
    videos = {}
    associations = {}

    events_payload, slides_payload = build_output_payloads(events, videos, associations, include_classes=False)

    assert events_payload["includeClasses"] is False
    assert events_payload["items"][0]["id"].startswith("event-jazz-night")
    assert slides_payload["slides"][0]["type"] == "event"
```

- [ ] **Step 5: Implement the output payload builder and run the tests**

```python
def build_output_payloads(
    events: list[dict[str, Any]],
    videos: dict[str, dict[str, Any]],
    associations: dict[str, str],
    include_classes: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_events = [normalize_event(item) for item in events]
    slides = build_slides(normalized_events, videos, associations)
    events_payload = {
        "fetchedAt": None,
        "includeClasses": include_classes,
        "sourceUrl": "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/",
        "total": len(normalized_events),
        "items": normalized_events,
        "lastError": None,
    }
    slides_payload = {
        "fetchedAt": None,
        "total": len(slides),
        "slides": slides,
    }
    return events_payload, slides_payload
```

Run: `python -m pytest tests/test_publisher.py tests/test_scraper.py -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add pi_display/models.py pi_display/scraper.py pi_display/publisher.py tests/test_scraper.py tests/test_publisher.py
git commit -m "feat: port event publishing and slide generation to python"
```

### Task 3: Add SQLite Storage For Video Assets And Associations

**Files:**
- Create: `pi_display/database.py`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Write the failing database test for storing an uploaded video and association**

```python
from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase


def test_database_stores_video_and_event_association(tmp_path):
    config = AppConfig.from_root(tmp_path)
    database = DisplayDatabase(config.database_path)
    database.initialize()

    database.save_video(
        video_id="video-jazz-trailer",
        title="Jazz Night Trailer",
        filename="jazz-night.mp4",
        storage_path="./cache/videos/jazz-night.mp4",
        mime_type="video/mp4",
        duration_seconds=20,
    )
    database.set_event_video(event_id="event-jazz-night-2026-06-01", video_id="video-jazz-trailer")

    videos = database.list_videos()
    associations = database.list_event_video_map()

    assert videos[0]["title"] == "Jazz Night Trailer"
    assert associations["event-jazz-night-2026-06-01"] == "video-jazz-trailer"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_database.py::test_database_stores_video_and_event_association -q`
Expected: `ImportError` for `DisplayDatabase`

- [ ] **Step 3: Implement the SQLite schema and repository methods**

```python
# pi_display/database.py
from __future__ import annotations

import sqlite3
from pathlib import Path


class DisplayDatabase:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                create table if not exists videos (
                    id text primary key,
                    title text not null,
                    filename text not null,
                    storage_path text not null,
                    poster_path text,
                    mime_type text not null,
                    duration_seconds integer,
                    enabled integer not null default 1,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );

                create table if not exists event_video_associations (
                    event_id text primary key,
                    video_id text not null references videos(id),
                    enabled integer not null default 1,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );
                """
            )

    def save_video(self, **payload) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into videos (id, title, filename, storage_path, poster_path, mime_type, duration_seconds, enabled)
                values (:video_id, :title, :filename, :storage_path, :poster_path, :mime_type, :duration_seconds, 1)
                on conflict(id) do update set
                    title=excluded.title,
                    filename=excluded.filename,
                    storage_path=excluded.storage_path,
                    poster_path=excluded.poster_path,
                    mime_type=excluded.mime_type,
                    duration_seconds=excluded.duration_seconds,
                    updated_at=current_timestamp
                """,
                {
                    "video_id": payload["video_id"],
                    "title": payload["title"],
                    "filename": payload["filename"],
                    "storage_path": payload["storage_path"],
                    "poster_path": payload.get("poster_path"),
                    "mime_type": payload["mime_type"],
                    "duration_seconds": payload.get("duration_seconds"),
                },
            )

    def list_videos(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("select * from videos order by created_at desc").fetchall()
        return [dict(row) for row in rows]

    def set_event_video(self, event_id: str, video_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into event_video_associations (event_id, video_id, enabled)
                values (?, ?, 1)
                on conflict(event_id) do update set
                    video_id=excluded.video_id,
                    enabled=1,
                    updated_at=current_timestamp
                """,
                (event_id, video_id),
            )

    def clear_event_video(self, event_id: str) -> None:
        with self.connect() as connection:
            connection.execute("delete from event_video_associations where event_id = ?", (event_id,))

    def list_event_video_map(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute(
                "select event_id, video_id from event_video_associations where enabled = 1"
            ).fetchall()
        return {row["event_id"]: row["video_id"] for row in rows}
```

- [ ] **Step 4: Run the database tests**

Run: `python -m pytest tests/test_database.py -q`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add pi_display/database.py tests/test_database.py
git commit -m "feat: add sqlite storage for videos and associations"
```

### Task 4: Build The Pi Web App And Refresh Command

**Files:**
- Create: `pi_display/web.py`
- Create: `pi_display/refresh.py`
- Create: `tests/test_web.py`

- [ ] **Step 1: Write the failing web test for uploading a video and linking it to an event**

```python
from io import BytesIO

from pi_display.web import create_app


def test_video_upload_and_association_flow(tmp_path):
    app = create_app(tmp_path)
    client = app.test_client()

    upload_response = client.post(
        "/api/videos",
        data={"file": (BytesIO(b"fake mp4 bytes"), "jazz-night.mp4")},
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    video_id = upload_response.get_json()["video"]["id"]

    association_response = client.put(
        "/api/video-associations/event-jazz-night-2026-06-01",
        json={"videoId": video_id},
    )
    assert association_response.status_code == 200
    assert association_response.get_json()["eventId"] == "event-jazz-night-2026-06-01"
```

- [ ] **Step 2: Run the web test to verify it fails**

Run: `python -m pytest tests/test_web.py::test_video_upload_and_association_flow -q`
Expected: `ImportError` for `create_app`

- [ ] **Step 3: Implement the Flask app, upload endpoint, association endpoint, and refresh entrypoint**

```python
# pi_display/web.py
from __future__ import annotations

import hashlib
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase


def create_app(root_dir: Path) -> Flask:
    config = AppConfig.from_root(Path(root_dir))
    database = DisplayDatabase(config.database_path)
    database.initialize()

    app = Flask(__name__, static_folder=str(config.public_dir), static_url_path="")
    app.config["APP_CONFIG"] = config
    app.config["DISPLAY_DATABASE"] = database

    @app.get("/")
    def index():
        return send_from_directory(config.public_dir, "index.html")

    @app.post("/api/videos")
    def upload_video():
        file = request.files.get("file")
        if file is None or file.filename == "":
            return jsonify({"error": "file is required"}), 400

        filename = secure_filename(file.filename)
        video_id = f"video-{hashlib.sha1(filename.encode('utf-8')).hexdigest()[:8]}"
        config.video_dir.mkdir(parents=True, exist_ok=True)
        destination = config.video_dir / filename
        file.save(destination)

        relative_path = f"./cache/videos/{filename}"
        database.save_video(
            video_id=video_id,
            title=Path(filename).stem.replace("-", " ").title(),
            filename=filename,
            storage_path=relative_path,
            mime_type=file.mimetype or "video/mp4",
            duration_seconds=None,
        )

        return jsonify({"video": {"id": video_id, "src": relative_path, "title": Path(filename).stem}}), 201

    @app.get("/api/videos")
    def list_videos():
        return jsonify({"items": database.list_videos()})

    @app.put("/api/video-associations/<event_id>")
    def set_video_association(event_id: str):
        payload = request.get_json(silent=True) or {}
        video_id = payload.get("videoId")
        if not video_id:
            return jsonify({"error": "videoId is required"}), 400
        database.set_event_video(event_id=event_id, video_id=video_id)
        return jsonify({"eventId": event_id, "videoId": video_id})

    @app.delete("/api/video-associations/<event_id>")
    def clear_video_association(event_id: str):
        database.clear_event_video(event_id)
        return jsonify({"eventId": event_id, "cleared": True})

    return app


def main() -> None:
    create_app(Path.cwd()).run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
```

```python
# pi_display/refresh.py
from __future__ import annotations

import json
from pathlib import Path

from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase
from pi_display.publisher import build_output_payloads
from pi_display.scraper import scrape_events


def refresh_site(root_dir: Path) -> None:
    config = AppConfig.from_root(Path(root_dir))
    database = DisplayDatabase(config.database_path)
    database.initialize()

    events = scrape_events(config, include_classes=False)
    videos = {video["id"]: video for video in database.list_videos()}
    associations = database.list_event_video_map()
    events_payload, slides_payload = build_output_payloads(events, videos, associations, include_classes=False)

    (config.public_dir / "events.json").write_text(json.dumps(events_payload, indent=2), encoding="utf-8")
    (config.public_dir / "slides.json").write_text(json.dumps(slides_payload, indent=2), encoding="utf-8")


def main() -> None:
    refresh_site(Path.cwd())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the web tests**

Run: `python -m pytest tests/test_web.py -q`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add pi_display/web.py pi_display/refresh.py tests/test_web.py
git commit -m "feat: add pi web app and video management api"
```

### Task 5: Add Dashboard Video Management UI

**Files:**
- Create: `public/video-admin-model.js`
- Modify: `public/index.html`
- Modify: `public/app.js`
- Modify: `public/styles.css`
- Create: `tests/app-view-model.test.mjs`

- [ ] **Step 1: Write the failing pure-JS test for formatting event association rows**

```javascript
import test from "node:test";
import assert from "node:assert/strict";

import { buildAssociationViewModel } from "../public/video-admin-model.js";

test("buildAssociationViewModel marks linked events", () => {
  const rows = buildAssociationViewModel(
    [{ id: "event-jazz", title: "Jazz Night" }],
    [{ id: "video-jazz", title: "Jazz Trailer" }],
    { "event-jazz": "video-jazz" }
  );

  assert.equal(rows[0].selectedVideoId, "video-jazz");
  assert.equal(rows[0].hasAssociation, true);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/app-view-model.test.mjs`
Expected: `SyntaxError` or missing export from `public/app.js`

- [ ] **Step 3: Add the dashboard markup for uploads and event/video associations**

```html
<section class="video-admin" aria-label="Promo video management">
  <div class="video-admin-header">
    <div>
      <p class="eyebrow">Promo videos</p>
      <h2>Associate videos with events</h2>
    </div>
    <form id="videoUploadForm" class="video-upload-form">
      <input id="videoUploadInput" name="file" type="file" accept="video/mp4,video/webm,video/ogg">
      <button type="submit">Upload video</button>
    </form>
  </div>
  <div id="videoUploadStatus" class="video-upload-status" aria-live="polite"></div>
  <div id="videoAssociationList" class="video-association-list"></div>
</section>

<script type="module" src="./app.js"></script>
```

- [ ] **Step 4: Implement the dashboard API calls and association rendering**

```javascript
// public/video-admin-model.js
export function buildAssociationViewModel(events, videos, associations) {
  return events.map((event) => ({
    eventId: event.id,
    title: event.title || "Untitled event",
    dateText: event.dateText || "Date TBC",
    selectedVideoId: associations[event.id] || "",
    hasAssociation: Boolean(associations[event.id]),
    options: videos.map((video) => ({ id: video.id, title: video.title || video.filename }))
  }));
}
```

```javascript
// public/app.js
import { buildAssociationViewModel } from "./video-admin-model.js";

async function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/videos", { method: "POST", body: formData });
  if (!response.ok) {
    throw new Error("Video upload failed");
  }
  return response.json();
}

async function saveVideoAssociation(eventId, videoId) {
  const response = await fetch(`/api/video-associations/${encodeURIComponent(eventId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ videoId })
  });
  if (!response.ok) {
    throw new Error("Association save failed");
  }
  return response.json();
}
```

- [ ] **Step 5: Add the admin styling and run the UI test**

```css
.video-admin {
  margin-top: 2rem;
  padding: 1.5rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 48px rgba(30, 36, 32, 0.12);
}

.video-association-list {
  display: grid;
  gap: 0.75rem;
}

.video-association-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px);
  gap: 1rem;
  align-items: center;
}
```

Run: `node --test tests/app-view-model.test.mjs`
Expected: `1 passing`

- [ ] **Step 6: Commit**

```bash
git add public/index.html public/app.js public/styles.css tests/app-view-model.test.mjs
git commit -m "feat: add dashboard video association ui"
```

### Task 6: Support Video Slides In Fullscreen Playback

**Files:**
- Create: `public/slide-sequence.js`
- Modify: `public/fullscreen.html`
- Modify: `public/fullscreen.js`
- Modify: `public/styles.css`
- Create: `tests/fullscreen-slides.test.mjs`

- [ ] **Step 1: Write the failing pure-JS test for choosing the next playable slide**

```javascript
import test from "node:test";
import assert from "node:assert/strict";

import { getNextRenderableSlide } from "../public/slide-sequence.js";

test("getNextRenderableSlide skips broken video slides", () => {
  const slides = [
    { type: "video", id: "video-1", src: "./cache/videos/missing.mp4", eventId: "event-1" },
    { type: "event", id: "event-1", title: "Jazz Night" }
  ];

  const nextSlide = getNextRenderableSlide(slides, 0, new Set(["video-1"]));

  assert.equal(nextSlide.id, "event-1");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/fullscreen-slides.test.mjs`
Expected: missing export from `public/fullscreen.js`

- [ ] **Step 3: Add the dedicated fullscreen video element**

```html
<div class="fullscreen-media">
  <video
    id="slideVideo"
    class="fullscreen-video"
    hidden
    muted
    playsinline
    preload="auto"
  ></video>
  <img id="slideImage" class="fullscreen-image" alt="" hidden>
  <div id="slidePoster" class="fullscreen-poster"></div>
  <div id="slideCategory" class="fullscreen-category"></div>
</div>

<script type="module" src="./fullscreen.js"></script>
```

- [ ] **Step 4: Implement slide-type aware playback**

```javascript
// public/slide-sequence.js
export function getNextRenderableSlide(slides, startIndex, failedVideoIds = new Set()) {
  for (let offset = 0; offset < slides.length; offset += 1) {
    const slide = slides[(startIndex + offset) % slides.length];
    if (slide.type !== "video") {
      return slide;
    }
    if (!failedVideoIds.has(slide.id) && slide.src) {
      return slide;
    }
  }
  return slides[startIndex] || null;
}
```

```javascript
// public/fullscreen.js
import { getNextRenderableSlide } from "./slide-sequence.js";

function renderVideoSlide(slide) {
  slideVideo.hidden = false;
  slideImage.hidden = true;
  slidePoster.hidden = true;
  slideQrPanel.hidden = true;
  slideTitle.textContent = slide.title || "Promo video";
  slideDate.textContent = "Starting now";
  slideDetails.innerHTML = "";
  slideVideo.src = normalizeAssetUrl(slide.src);
  slideVideo.currentTime = 0;
  slideVideo.play().catch(() => {
    state.failedVideoIds.add(slide.id);
    advanceToNextSlide();
  });
}
```

- [ ] **Step 5: Add fullscreen video styling and run the tests**

```css
.fullscreen-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 1.25rem;
  background: #000;
}
```

Run: `node --test tests/fullscreen-slides.test.mjs`
Expected: `1 passing`

- [ ] **Step 6: Smoke-test the browser flow**

Run: `python -m pi_display.web`
Expected: the dashboard loads, the upload UI appears, `public/slides.json` is served, and a linked video slide plays before its event slide

- [ ] **Step 7: Commit**

```bash
git add public/fullscreen.html public/fullscreen.js public/styles.css tests/fullscreen-slides.test.mjs
git commit -m "feat: add fullscreen video slide playback"
```

### Task 7: Ship Pi Refresh Tooling And Documentation

**Files:**
- Create: `systemd/acw-display.service`
- Create: `systemd/acw-refresh.service`
- Create: `systemd/acw-refresh.timer`
- Modify: `README.md`

- [ ] **Step 1: Write the failing documentation checklist in the README**

```markdown
- [ ] Raspberry Pi setup instructions
- [ ] Python dependency installation
- [ ] systemd service and timer setup
- [ ] video upload and association workflow
- [ ] fallback note for GitHub Pages and Windows testing
```

- [ ] **Step 2: Add the systemd units**

```ini
# systemd/acw-display.service
[Unit]
Description=ACW display web app
After=network.target

[Service]
WorkingDirectory=/opt/acw-screen-updater
ExecStart=/usr/bin/python -m pi_display.web
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# systemd/acw-refresh.service
[Unit]
Description=Refresh ACW display data
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/acw-screen-updater
ExecStart=/usr/bin/python -m pi_display.refresh
```

```ini
# systemd/acw-refresh.timer
[Unit]
Description=Schedule ACW display refresh

[Timer]
OnBootSec=2m
OnUnitActiveSec=5m
Unit=acw-refresh.service

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Update the README with Pi-first setup and operator flow**

```markdown
## Raspberry Pi production setup

1. Clone the repository onto the Pi.
2. Install Python 3 and the dependencies from `requirements.txt`.
3. Run `python -m pi_display.refresh` once to create `public/events.json` and `public/slides.json`.
4. Start the Flask app or install the provided `systemd/` units.
5. Open the dashboard, upload promo videos, and associate them with event rows.

Production note: the Raspberry Pi-hosted version is now the primary deployment target. GitHub Pages remains a fallback preview target, and the old PowerShell flow remains useful for local testing while the migration is underway.
```

- [ ] **Step 4: Run the final verification**

Run: `python -m pytest tests/test_database.py tests/test_publisher.py tests/test_scraper.py tests/test_web.py -q`
Expected: all Python tests pass

Run: `node --test tests/app-view-model.test.mjs tests/fullscreen-slides.test.mjs`
Expected: all JavaScript tests pass

- [ ] **Step 5: Commit**

```bash
git add systemd/acw-display.service systemd/acw-refresh.service systemd/acw-refresh.timer README.md
git commit -m "docs: add pi deployment and operator guidance"
```

## Self-Review

- Spec coverage: Pi hosting, scheduled publishing, SQLite storage, upload and association UI, generated slide output, fullscreen `video -> event` sequencing, and deployment guidance are all covered by Tasks 1-7.
- Placeholder scan: no `TODO`, `TBD`, or "implement later" placeholders remain in the task steps.
- Type consistency: the plan consistently uses `eventId`, `videoId`, `slides.json`, `public/cache/videos/`, and `DisplayDatabase`.
