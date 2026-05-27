import json
import shutil
import uuid
from pathlib import Path

from pi_display.scraper import scrape_events_from_fixture


def test_scrape_events_from_fixture_reads_items():
    root_dir = Path.cwd() / ".tmp" / f"scraper-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        source_path = root_dir / "events.json"
        source_path.write_text(json.dumps([{"title": "Jazz Night"}]), encoding="utf-8")

        items = scrape_events_from_fixture(source_path)

        assert items == [{"title": "Jazz Night"}]
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)
