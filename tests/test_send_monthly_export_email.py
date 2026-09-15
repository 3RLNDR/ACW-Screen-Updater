from __future__ import annotations

import importlib.util
from pathlib import Path


def load_email_module():
    script_path = Path.cwd() / "scripts" / "send_monthly_export_email.py"
    spec = importlib.util.spec_from_file_location("send_monthly_export_email", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_build_email_body_includes_friendly_summary_and_event_list():
    module = load_email_module()
    manifest = {
        "windowLabel": "June-September 2026",
        "generatedCount": 20,
        "warnings": [],
        "events": [
            {"title": "Song Sung Blue", "date": "03 Jun 2026"},
            {"title": "Sherlock Holmes and The Sting of the Scorpion", "date": "04 Jun 2026"},
        ],
    }

    body = module.build_email_body(manifest, "https://example.com/download")

    assert "attached ZIP includes ready-to-use slideshow JPGs in both 16:9 and 4:3 formats" in body
    assert "Included in this pack:" in body
    assert "- Song Sung Blue - 03 Jun 2026" in body
    assert "- Sherlock Holmes and The Sting of the Scorpion - 04 Jun 2026" in body
    assert "Download: https://example.com/download" in body
