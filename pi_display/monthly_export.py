from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from pi_display.config import AppConfig
from pi_display.monthly_template import get_ratio_spec


@dataclass(frozen=True)
class ExportWindow:
    start: date
    end: date
    label: str


def last_day_of_month(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + offset
    end_year, zero_based_month = divmod(month_index, 12)
    return end_year, zero_based_month + 1


def is_three_days_before_month_end(today: date) -> bool:
    return today == last_day_of_month(today) - timedelta(days=3)


def build_export_window(run_date: date) -> ExportWindow:
    end_year, end_month = add_months(run_date.year, run_date.month, 3)
    end = date(end_year, end_month, monthrange(end_year, end_month)[1])
    label = f"{run_date.strftime('%B')}-{end.strftime('%B %Y')}"
    return ExportWindow(start=run_date, end=end, label=label)


def normalize_export_text(value: str | None) -> str:
    return (
        str(value or "")
        .replace("Ãƒâ€šÃ‚Â£", "£")
        .replace("–", "-")
        .replace("—", "-")
        .strip()
    )


def select_export_events(items: list[dict], start_iso: str, end_iso: str) -> list[dict]:
    start = datetime.fromisoformat(start_iso).date()
    end = datetime.fromisoformat(end_iso).date()
    selected: list[dict] = []
    for item in items:
        if item.get("isClass"):
            continue
        sort_value = item.get("sortDate")
        if not sort_value:
            continue
        sort_date = datetime.fromisoformat(sort_value).date()
        if start <= sort_date <= end:
            selected.append(item)
    return selected


def format_export_date_lines(item: dict) -> tuple[str, str]:
    category = normalize_export_text(item.get("category")).lower()
    date_text = normalize_export_text(item.get("dateText"))
    if category != "exhibitions":
        bits = [date_text]
        if item.get("startTime"):
            bits.append(normalize_export_text(item.get("startTime")))
        return " | ".join([bit for bit in bits if bit]), ""

    meta = item.get("meta") or []
    primary = normalize_export_text(meta[0]) if meta else date_text
    note = f"Open until {date_text}" if date_text else ""
    return primary, note


def slugify_filename(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_export_text(value).lower()).strip("-")


def build_export_filename(item: dict) -> str:
    sort_date = datetime.fromisoformat(item["sortDate"]).strftime("%Y-%m-%d")
    return f"{sort_date}-{slugify_filename(item['title'])}.jpg"


def build_manifest(window_label: str, selected_count: int, generated_count: int, warnings: list[dict]) -> dict:
    return {
        "windowLabel": window_label,
        "selectedCount": selected_count,
        "generatedCount": generated_count,
        "warnings": warnings,
    }


def ensure_ratio_dirs(output_dir: Path) -> tuple[Path, Path]:
    wide = output_dir / "16x9"
    standard = output_dir / "4x3"
    wide.mkdir(parents=True, exist_ok=True)
    standard.mkdir(parents=True, exist_ok=True)
    return wide, standard


def get_palette(category: str | None) -> tuple[str, str, str]:
    palette = {
        "theatre and performance": ("#7a2e23", "#f4e6d7", "#1f1714"),
        "special events": ("#8c5a18", "#f7ead0", "#1f180f"),
        "music": ("#15505d", "#dff4f2", "#102326"),
        "films": ("#243c6b", "#e4ecff", "#10172a"),
        "exhibitions": ("#2b5b41", "#e0f2e8", "#132119"),
        "comedy": ("#8f3b52", "#f7dfe6", "#25151a"),
        "talks": ("#6f4a37", "#f1e1d3", "#241915"),
    }
    return palette.get(normalize_export_text(category).lower(), ("#31463f", "#e9efe9", "#17211e"))


def resolve_public_asset_path(project_root: Path, asset_path: str | None) -> Path | None:
    if not asset_path:
        return None
    candidate = project_root / "public" / asset_path
    if candidate.exists():
        return candidate
    return None


def build_render_spec(project_root: Path, item: dict, ratio: str, output_file: Path) -> dict:
    spec = get_ratio_spec(ratio)
    brand_color, panel_color, ink_color = get_palette(item.get("category"))
    meta_line, note_line = format_export_date_lines(item)
    image_path = resolve_public_asset_path(project_root, item.get("imageLocal"))
    qr_path = resolve_public_asset_path(project_root, item.get("qrLocal"))
    return {
        "width": spec.width,
        "height": spec.height,
        "imageWidth": spec.image_width,
        "imageHeight": spec.image_height,
        "panelX": spec.panel_x,
        "panelWidth": spec.panel_width,
        "categoryX": spec.category_x,
        "categoryY": spec.category_y,
        "titleX": spec.title_x,
        "titleY": spec.title_y,
        "titleWidth": spec.title_width,
        "metaX": spec.meta_x,
        "metaY": spec.meta_y,
        "noteX": spec.note_x,
        "noteY": spec.note_y,
        "qrX": spec.qr_x,
        "qrY": spec.qr_y,
        "qrSize": spec.qr_size,
        "panelColor": panel_color,
        "brandColor": brand_color,
        "inkColor": ink_color,
        "category": normalize_export_text(item.get("category")).upper(),
        "title": normalize_export_text(item.get("title")),
        "metaLine": meta_line,
        "noteLine": note_line,
        "imagePath": str(image_path) if image_path else "",
        "qrPath": str(qr_path) if qr_path else "",
        "outputPath": str(output_file),
    }


def render_slide_jpg(item: dict, ratio: str, output_file: Path, project_root: Path) -> None:
    render_script = Path(__file__).resolve().parent.parent / "scripts" / "render-monthly-export-slide.ps1"
    spec_path = output_file.with_suffix(".json")
    spec_path.write_text(
        json.dumps(build_render_spec(project_root=project_root, item=item, ratio=ratio, output_file=output_file), indent=2),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(render_script),
                "-SpecPath",
                str(spec_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        spec_path.unlink(missing_ok=True)


def render_monthly_export_pack(project_root: Path, output_dir: Path, items: list[dict], window_label: str) -> dict:
    wide_dir, standard_dir = ensure_ratio_dirs(output_dir)
    generated_files: list[Path] = []
    warnings: list[dict] = []

    for item in items:
        filename = build_export_filename(item)
        for ratio, target_dir in (("16x9", wide_dir), ("4x3", standard_dir)):
            output_file = target_dir / filename
            render_slide_jpg(item=item, ratio=ratio, output_file=output_file, project_root=project_root)
            generated_files.append(output_file)

    manifest = build_manifest(
        window_label=window_label,
        selected_count=len(items),
        generated_count=len(generated_files),
        warnings=warnings,
    )
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def create_export_zip(output_dir: Path, zip_name: str) -> Path:
    zip_path = output_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in output_dir.rglob("*"):
            if file_path == zip_path or file_path.is_dir():
                continue
            archive.write(file_path, file_path.relative_to(output_dir))
    return zip_path


def run_monthly_export(root_dir: Path | str, payload: dict, run_date_iso: str, output_dir: Path | None = None) -> dict:
    run_date = datetime.fromisoformat(run_date_iso).date()
    window = build_export_window(run_date)
    project_root = Path(root_dir)
    export_dir = output_dir or (project_root / "output" / "monthly-export")
    export_dir.mkdir(parents=True, exist_ok=True)
    items = select_export_events(
        payload.get("items", []),
        start_iso=window.start.isoformat(),
        end_iso=window.end.isoformat(),
    )
    manifest = render_monthly_export_pack(project_root=project_root, output_dir=export_dir, items=items, window_label=window.label)
    zip_path = create_export_zip(export_dir, f"acw-monthly-slides-{run_date.strftime('%Y-%m')}.zip")
    return {
        "windowLabel": window.label,
        "selectedCount": manifest["selectedCount"],
        "generatedCount": manifest["generatedCount"],
        "zipPath": str(zip_path),
    }


def load_events_payload(root_dir: Path) -> dict:
    events_path = root_dir / "public" / "events.json"
    return json.loads(events_path.read_text(encoding="utf-8-sig"))


def main() -> None:
    config = AppConfig.from_root(Path.cwd())
    output_dir = config.root_dir / "output" / "monthly-export"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = load_events_payload(config.root_dir)
    run_monthly_export(config.root_dir, payload, datetime.now().date().isoformat(), output_dir=output_dir)


if __name__ == "__main__":
    main()
