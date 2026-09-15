from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from pi_display.config import AppConfig
from pi_display.monthly_template import get_ratio_spec

FONT_ASSETS = {
    "category": "assets/fonts/Montserrat-SemiBold.ttf",
    "title": "assets/fonts/Montserrat-Bold.ttf",
}
REPO_ROOT = Path(__file__).resolve().parent.parent


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


def build_manifest_event(item: dict) -> dict:
    category = normalize_export_text(item.get("category")).lower()
    if category == "exhibitions":
        meta = item.get("meta") or []
        date_label = normalize_export_text(meta[0]) if meta else normalize_export_text(item.get("dateText"))
    else:
        date_label = normalize_export_text(item.get("dateText"))
    return {
        "title": normalize_export_text(item.get("title")),
        "date": date_label,
    }


def build_manifest(
    window_label: str,
    selected_count: int,
    generated_count: int,
    warnings: list[dict],
    events: list[dict],
) -> dict:
    return {
        "windowLabel": window_label,
        "selectedCount": selected_count,
        "generatedCount": generated_count,
        "warnings": warnings,
        "events": events,
    }


def ensure_ratio_dirs(output_dir: Path) -> tuple[Path, Path]:
    wide = output_dir / "16x9"
    standard = output_dir / "4x3"
    wide.mkdir(parents=True, exist_ok=True)
    standard.mkdir(parents=True, exist_ok=True)
    return wide, standard


HOUSE_PALETTE = {
    "brandColor": "#5f3a2d",
    "panelColor": "#fcf5ea",
    "inkColor": "#1f1714",
    "noteColor": "#4d544c",
}


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def estimate_visual_title_units(title: str) -> float:
    units = 0.0
    for char in title:
        if char in "MW&":
            units += 1.55
        elif char.isupper():
            units += 1.28
        elif char in "mqw":
            units += 1.18
        elif char in "il.,:' ":
            units += 0.42
        else:
            units += 0.92
    return units


def estimate_title_lines(title: str, title_width: int, font_size: int) -> int:
    if not title:
        return 1
    average_unit_width = max(font_size * 0.66, 1)
    units_per_line = max(title_width / average_unit_width, 6)
    visual_units = estimate_visual_title_units(title)
    occupancy = visual_units / units_per_line
    if occupancy > 0.88 and len(title.split()) >= 4:
        return 2
    return max(1, math.ceil(occupancy))


def wrap_title_text(title: str, title_width: int, font_size: int, max_lines: int) -> list[str]:
    words = title.split()
    if not words:
        return [title]

    average_unit_width = max(font_size * 0.72, 1)
    units_per_line = max(title_width / average_unit_width, 5)
    lines: list[str] = []
    current_words: list[str] = []
    current_units = 0.0

    for word in words:
        word_units = estimate_visual_title_units(word)
        spacer_units = 0.45 if current_words else 0.0
        if current_words and current_units + spacer_units + word_units > units_per_line and len(lines) < max_lines - 1:
            lines.append(" ".join(current_words))
            current_words = [word]
            current_units = word_units
            continue
        current_words.append(word)
        current_units += spacer_units + word_units

    if current_words:
        lines.append(" ".join(current_words))

    if len(lines) > max_lines:
        kept = lines[: max_lines - 1]
        kept.append(" ".join(lines[max_lines - 1 :]))
        lines = kept

    return lines


def force_balanced_title_break(title: str) -> list[str]:
    words = title.split()
    if len(words) < 4:
        return [title]
    midpoint = max(2, len(words) // 2)
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def build_title_layout(title: str, title_width: int, ratio: str) -> dict[str, int]:
    word_count = len(title.split())
    if ratio == "16x9":
        max_size = 32
        min_size = 22
        max_lines = 4
    else:
        max_size = 26
        min_size = 20
        max_lines = 4

    font_size = max_size
    while font_size > min_size:
        line_count = estimate_title_lines(title, title_width=title_width, font_size=font_size)
        if line_count <= max_lines:
            break
        font_size -= 1

    title_length = len(title)
    if title_length > 56:
        font_size -= 10
    elif title_length > 44:
        font_size -= 5
    elif title_length > 32:
        font_size -= 3
    font_size = clamp(font_size, min_size, max_size)
    wrapped_lines = wrap_title_text(title, title_width=title_width, font_size=font_size, max_lines=max_lines)
    line_count = len(wrapped_lines)
    if word_count >= 4 and line_count < 2:
        wrapped_lines = force_balanced_title_break(title)
        line_count = len(wrapped_lines)
    line_height = int(font_size * 1.22)
    return {
        "titleFontSize": font_size,
        "titleMinFontSize": min_size,
        "titleMaxLines": max_lines,
        "titleLineCount": line_count,
        "titleLineHeight": line_height,
        "titleLineHeightFactor": 1.22,
        "titleBoxHeight": (line_count * line_height) + 12,
        "titleText": "\n".join(wrapped_lines),
    }


def is_free_event(item: dict) -> bool:
    values = [
        normalize_export_text(item.get("cost")).lower(),
        normalize_export_text(item.get("status")).lower(),
    ]
    return any(value == "free" for value in values)


def get_qr_prompt(item: dict) -> str:
    return "Find out more" if is_free_event(item) else "Scan to book"


def resolve_public_asset_path(project_root: Path, asset_path: str | None) -> Path | None:
    if not asset_path:
        return None
    candidate = project_root / "public" / asset_path
    if candidate.exists():
        return candidate
    return None


def resolve_font_asset_path(project_root: Path, asset_key: str) -> Path:
    relative_path = Path(FONT_ASSETS[asset_key])
    for root in (project_root, REPO_ROOT):
        candidate = root / relative_path
        if candidate.exists():
            return candidate.resolve()
    return (REPO_ROOT / relative_path).resolve()


def build_render_spec(project_root: Path, item: dict, ratio: str, output_file: Path) -> dict:
    spec = get_ratio_spec(ratio)
    title = normalize_export_text(item.get("title"))
    title_layout = build_title_layout(title=title, title_width=spec.title_width, ratio=ratio)
    meta_line, note_line = format_export_date_lines(item)
    image_path = resolve_public_asset_path(project_root, item.get("imageLocal"))
    qr_path = resolve_public_asset_path(project_root, item.get("qrLocal"))
    category_font_size = 20 if ratio == "16x9" else 18
    meta_font_size = 24 if ratio == "16x9" else 22
    note_font_size = 18 if ratio == "16x9" else 17
    qr_prompt_font_size = 15 if ratio == "16x9" else 14
    qr_container_padding = 16
    qr_prompt_gap = 12 if ratio == "16x9" else 14
    qr_prompt_y = spec.qr_y - qr_container_padding - qr_prompt_font_size - qr_prompt_gap
    meta_line_height = meta_font_size + 10
    note_line_height = note_font_size + 8
    meta_y = max(spec.meta_y, spec.title_y + title_layout["titleBoxHeight"] + 54)
    note_y = meta_y + meta_line_height + 16 if note_line else spec.note_y

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
        "titleBoxHeight": title_layout["titleBoxHeight"],
        "titleFontSize": title_layout["titleFontSize"],
        "titleMinFontSize": title_layout["titleMinFontSize"],
        "titleMaxLines": title_layout["titleMaxLines"],
        "titleLineHeight": title_layout["titleLineHeight"],
        "titleLineHeightFactor": title_layout["titleLineHeightFactor"],
        "metaX": spec.meta_x,
        "metaY": meta_y,
        "metaFontSize": meta_font_size,
        "metaLineHeight": meta_line_height,
        "noteX": spec.note_x,
        "noteY": note_y,
        "noteFontSize": note_font_size,
        "noteLineHeight": note_line_height,
        "qrX": spec.qr_x,
        "qrY": spec.qr_y,
        "qrSize": spec.qr_size,
        "qrContainerPadding": qr_container_padding,
        "panelColor": HOUSE_PALETTE["panelColor"],
        "brandColor": HOUSE_PALETTE["brandColor"],
        "inkColor": HOUSE_PALETTE["inkColor"],
        "noteColor": HOUSE_PALETTE["noteColor"],
        "categoryFontFamily": "Montserrat",
        "titleFontFamily": "Montserrat",
        "metaFontFamily": "Arial",
        "noteFontFamily": "Arial",
        "categoryFontFile": str(resolve_font_asset_path(project_root, "category")),
        "titleFontFile": str(resolve_font_asset_path(project_root, "title")),
        "categoryFontSize": category_font_size,
        "category": normalize_export_text(item.get("category")).upper(),
        "titleRaw": title,
        "title": title_layout["titleText"],
        "metaLine": meta_line,
        "noteLine": note_line,
        "qrPrompt": get_qr_prompt(item),
        "qrPromptFontSize": qr_prompt_font_size,
        "qrPromptGap": qr_prompt_gap,
        "qrPromptY": qr_prompt_y,
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
        events=[build_manifest_event(item) for item in items],
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
