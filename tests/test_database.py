import shutil
import uuid
from pathlib import Path

from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase


def test_default_runtime_paths_live_inside_repo():
    root_dir = Path.cwd() / ".tmp" / f"config-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        config = AppConfig.from_root(root_dir)

        assert config.public_dir == root_dir / "public"
        assert config.video_dir == root_dir / "public" / "cache" / "videos"
        assert config.database_path == root_dir / "data" / "acw-display.sqlite3"
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)


def test_database_stores_video_and_event_association():
    root_dir = Path.cwd() / ".tmp" / f"database-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        config = AppConfig.from_root(root_dir)
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
        database.set_event_video(
            event_id="event-jazz-night-2026-06-01",
            video_id="video-jazz-trailer",
        )

        videos = database.list_videos()
        associations = database.list_event_video_map()

        assert videos[0]["title"] == "Jazz Night Trailer"
        assert associations["event-jazz-night-2026-06-01"] == "video-jazz-trailer"
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)
