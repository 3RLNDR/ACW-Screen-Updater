import base64
from datetime import date
from pathlib import Path
import shutil
import uuid

from pi_display.monthly_export import (
    build_export_filename,
    build_manifest,
    build_render_spec,
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
        events=[{"title": "Stage Show", "date": "04 Jun 2026"}],
    )

    assert manifest["windowLabel"] == "May-August 2026"
    assert manifest["selectedCount"] == 4
    assert manifest["generatedCount"] == 8
    assert manifest["warnings"][0]["reason"] == "missing qr"
    assert manifest["events"][0]["title"] == "Stage Show"


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


def test_build_render_spec_uses_shared_palette_across_categories():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    film_spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "category": "Films"},
        ratio="16x9",
        output_file=output_file,
    )
    exhibition_spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "category": "Exhibitions"},
        ratio="16x9",
        output_file=output_file,
    )

    assert film_spec["panelColor"] == exhibition_spec["panelColor"]
    assert film_spec["brandColor"] == exhibition_spec["brandColor"]
    assert film_spec["inkColor"] == exhibition_spec["inkColor"]


def test_build_render_spec_uses_bundled_montserrat_assets():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item=build_render_item(),
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["categoryFontFile"].replace("\\", "/").endswith("assets/fonts/Montserrat-SemiBold.ttf")
    assert spec["titleFontFile"].replace("\\", "/").endswith("assets/fonts/Montserrat-Bold.ttf")


def test_build_render_spec_uses_find_out_more_for_free_events():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "cost": "Free", "status": "Free"},
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["qrPrompt"] == "Find out more"


def test_build_render_spec_uses_scan_to_book_for_paid_events():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "cost": "£12", "status": ""},
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["qrPrompt"] == "Scan to book"


def test_build_render_spec_uses_approved_typography_defaults():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item=build_render_item(),
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["categoryFontFamily"] == "Montserrat"
    assert spec["titleFontFamily"] == "Montserrat"
    assert spec["metaFontFamily"] == "Arial"


def test_build_render_spec_keeps_4x3_qr_prompt_clear_of_qr_container():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "cost": "Free", "status": "Free"},
        ratio="4x3",
        output_file=output_file,
    )

    assert spec["qrPromptY"] + spec["qrPromptFontSize"] <= spec["qrY"] - spec["qrContainerPadding"] - spec["qrPromptGap"]


def test_build_render_spec_reduces_title_font_for_long_titles():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    short_spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "title": "Song Sung Blue"},
        ratio="16x9",
        output_file=output_file,
    )
    long_spec = build_render_spec(
        project_root=project_root,
        item={
            **build_render_item(),
            "title": "A Good Company of Musick: Royal Northern Sinfonia with Ben Lunn",
        },
        ratio="16x9",
        output_file=output_file,
    )

    assert long_spec["titleFontSize"] < short_spec["titleFontSize"]
    assert long_spec["titleLineHeight"] <= short_spec["titleLineHeight"]


def test_build_render_spec_wraps_wide_medium_length_titles():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "title": "Summer Craft & Makers Fair"},
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["titleBoxHeight"] > spec["titleLineHeight"]


def test_build_render_spec_wraps_summer_craft_title_without_ellipsis_pressure():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "title": "Summer Craft & Makers Fair"},
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["titleBoxHeight"] >= spec["titleLineHeight"] * 2
    assert "\n" in spec["title"]
    assert spec["titleFontSize"] >= 32


def test_build_render_spec_reduces_montserrat_title_for_long_music_event():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    short_spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "title": "Song Sung Blue"},
        ratio="16x9",
        output_file=output_file,
    )
    long_spec = build_render_spec(
        project_root=project_root,
        item={
            **build_render_item(),
            "title": "A Good Company of Musick: Royal Northern Sinfonia with Ben Lunn",
        },
        ratio="16x9",
        output_file=output_file,
    )

    assert long_spec["titleFontSize"] < short_spec["titleFontSize"]
    assert long_spec["titleBoxHeight"] > short_spec["titleBoxHeight"]
    assert "\n" in long_spec["title"]
    assert long_spec["titleFontSize"] <= 22


def test_build_render_spec_keeps_4x3_medium_titles_more_prominent_than_long_titles():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    medium_spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "title": "Summer Craft & Makers Fair"},
        ratio="4x3",
        output_file=output_file,
    )
    long_spec = build_render_spec(
        project_root=project_root,
        item={
            **build_render_item(),
            "title": "A Good Company of Musick: Royal Northern Sinfonia with Ben Lunn",
        },
        ratio="4x3",
        output_file=output_file,
    )

    assert medium_spec["titleFontSize"] >= 26
    assert long_spec["titleFontSize"] <= 20


def test_build_render_spec_separates_exhibition_note_from_primary_date():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    exhibition_spec = build_render_spec(
        project_root=project_root,
        item={
            **build_render_item(),
            "category": "Exhibitions",
            "title": "Broken",
            "dateText": "06 Jun 2026",
            "meta": ["30 Apr - 06 Jun 2026"],
            "startTime": "",
        },
        ratio="16x9",
        output_file=output_file,
    )

    assert exhibition_spec["noteLine"] == "Open until 06 Jun 2026"
    assert exhibition_spec["noteY"] >= exhibition_spec["metaY"] + exhibition_spec["metaLineHeight"] + 12


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
