from __future__ import annotations

import json
from pathlib import Path

from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase
from pi_display.publisher import build_output_payloads
from pi_display.scraper import scrape_events


def refresh_site(root_dir: Path | str) -> tuple[dict, dict]:
    config = AppConfig.from_root(Path(root_dir))
    for directory in (config.public_dir, config.video_dir, config.image_dir, config.qr_dir, config.data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    database = DisplayDatabase(config.database_path)
    database.initialize()
    events = scrape_events(config, include_classes=True)
    videos = database.get_video_map()
    associations = database.list_event_video_map()

    events_payload, slides_payload = build_output_payloads(
        events,
        videos=videos,
        associations=associations,
        include_classes=True,
    )

    (config.public_dir / "events.json").write_text(json.dumps(events_payload, indent=2), encoding="utf-8")
    (config.public_dir / "slides.json").write_text(json.dumps(slides_payload, indent=2), encoding="utf-8")
    return events_payload, slides_payload


def main() -> None:
    refresh_site(Path.cwd())


if __name__ == "__main__":
    main()
