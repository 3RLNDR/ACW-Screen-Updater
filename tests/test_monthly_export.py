import base64
from datetime import date
from pathlib import Path
import shutil
import uuid

from pi_display.monthly_export import (
    build_export_filename,
    build_manifest,
    build_export_window,
    format_export_date_lines,
    is_three_days_before_month_end,
    render_monthly_export_pack,
    run_monthly_export,
    select_export_events,
)


def test_is_three_days_before_month_end_true_for_may_28_2026():
    assert is_three_days_before_month_end(date(2026, 5, 28)) is True


def test_is_three_days_before_month_end_false_for_may_27_2026():
    assert is_three_days_before_month_end(date(2026, 5, 27)) is False


def test_build_export_window_covers_run_date_through_end_of_third_month():
    window = build_export_window(date(2026, 5, 28))

    assert window.start.isoformat() == "2026-05-28"
    assert window.end.isoformat() == "2026-08-31"
    assert window.label == "May-August 2026"


def test_select_export_events_excludes_classes_and_out_of_window_items():
    items = [
        {
            "title": "Stage Show",
            "dateText": "04 Jun 2026",
            "sortDate": "2026-06-04T00:00:00",
            "isClass": False,
        },
        {
            "title": "Workshop",
            "dateText": "05 Jun 2026",
            "sortDate": "2026-06-05T00:00:00",
            "isClass": True,
        },
        {
            "title": "Future Show",
            "dateText": "02 Sep 2026",
            "sortDate": "2026-09-02T00:00:00",
            "isClass": False,
        },
    ]

    selected = select_export_events(items, start_iso="2026-05-28", end_iso="2026-08-31")

    assert [item["title"] for item in selected] == ["Stage Show"]


def test_format_export_date_lines_for_exhibition_uses_open_until_note():
    item = {
        "category": "Exhibitions",
        "dateText": "06 Jun 2026",
        "meta": ["30 Apr - 06 Jun 2026"],
    }

    primary, note = format_export_date_lines(item)

    assert primary == "30 Apr - 06 Jun 2026"
    assert note == "Open until 06 Jun 2026"


def test_format_export_date_lines_for_standard_event_includes_start_time():
    item = {
        "category": "Theatre and Performance",
        "dateText": "04 Jun 2026",
        "startTime": "7:30pm",
    }

    primary, note = format_export_date_lines(item)

    assert primary == "04 Jun 2026 | 7:30pm"
    assert note == ""


def test_build_export_filename_uses_sortable_slug():
    item = {
        "title": "Sherlock Holmes and The Sting of the Scorpion",
        "sortDate": "2026-06-04T00:00:00",
    }

    assert build_export_filename(item) == "2026-06-04-sherlock-holmes-and-the-sting-of-the-scorpion.jpg"


def test_build_manifest_captures_counts_and_warnings():
    manifest = build_manifest(
        window_label="May-August 2026",
        selected_count=4,
        generated_count=8,
        warnings=[{"title": "Broken Link Event", "reason": "missing qr"}],
    )

    assert manifest["windowLabel"] == "May-August 2026"
    assert manifest["selectedCount"] == 4
    assert manifest["generatedCount"] == 8
    assert manifest["warnings"][0]["reason"] == "missing qr"


def write_asset(path: Path, encoded: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(encoded))


PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+yF9kAAAAASUVORK5CYII="


def build_render_item() -> dict:
    return {
        "title": "Sherlock Holmes",
        "category": "Theatre and Performance",
        "dateText": "04 Jun 2026",
        "startTime": "7:30pm",
        "sortDate": "2026-06-04T00:00:00",
        "imageLocal": "cache/images/example.png",
        "qrLocal": "cache/qr/example.png",
        "meta": [],
        "isClass": False,
    }


def test_render_monthly_export_pack_creates_both_ratio_folders():
    root_dir = Path.cwd() / ".tmp" / f"monthly-render-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        write_asset(root_dir / "public" / "cache" / "images" / "example.png", PNG_1X1)
        write_asset(root_dir / "public" / "cache" / "qr" / "example.png", PNG_1X1)

        output_dir = root_dir / "output" / "monthly-export"
        manifest = render_monthly_export_pack(
            project_root=root_dir,
            output_dir=output_dir,
            items=[build_render_item()],
            window_label="May-August 2026",
        )

        assert manifest["generatedCount"] == 2
        assert (output_dir / "16x9" / "2026-06-04-sherlock-holmes.jpg").exists()
        assert (output_dir / "4x3" / "2026-06-04-sherlock-holmes.jpg").exists()
        assert (output_dir / "manifest.json").exists()
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)


def test_run_monthly_export_writes_manifest_and_zip():
    root_dir = Path.cwd() / ".tmp" / f"monthly-run-{uuid.uuid4().hex}"
    root_dir.mkdir(parents=True, exist_ok=True)
    try:
        write_asset(root_dir / "public" / "cache" / "images" / "example.png", PNG_1X1)
        write_asset(root_dir / "public" / "cache" / "qr" / "example.png", PNG_1X1)

        payload = {"items": [build_render_item()]}

        result = run_monthly_export(root_dir=root_dir, payload=payload, run_date_iso="2026-05-28")

        assert result["zipPath"].endswith(".zip")
        assert (root_dir / "output" / "monthly-export" / "manifest.json").exists()
    finally:
        shutil.rmtree(root_dir, ignore_errors=True)
