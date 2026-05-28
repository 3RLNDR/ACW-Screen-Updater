# Monthly Slide Export Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled GitHub Actions workflow that generates monthly `16:9` and `4:3` JPG slide exports for upcoming events, zips them, and emails a download link three days before month-end.

**Architecture:** Reuse the existing normalized event payload as the source of truth, add a deterministic monthly-export renderer in Python, produce a manifest plus ZIP artifact, and orchestrate the flow through a dedicated GitHub Actions workflow with a date gate and email step.

**Tech Stack:** Python, pytest, GitHub Actions, existing `pi_display` data pipeline, static asset cache under `public/cache/`

---

## File Structure

### New files

- `pi_display/monthly_export.py`
  - Date window selection, event filtering, exhibition date formatting, filename generation, output manifest, ZIP creation, and high-level export orchestration.
- `pi_display/monthly_template.py`
  - Layout-specific rendering helpers for the approved monthly-pack slide design in `16:9` and `4:3`.
- `tests/test_monthly_export.py`
  - Unit tests for date gating, event selection, exhibition formatting, filename generation, manifest creation, and ZIP contents.
- `scripts/send_monthly_export_email.py`
  - Reads the generated manifest and download URL context, then sends the operational email through SMTP using GitHub secrets.
- `.github/workflows/monthly-slide-export.yml`
  - Scheduled workflow, manual dispatch, date gate, export run, artifact upload, and email delivery.
- `docs/superpowers/plans/2026-05-27-monthly-slide-export-email.md`
  - This implementation plan.

### Existing files to modify

- `pi_display/config.py`
  - Add export output directory helpers if the new module benefits from config-based path resolution.
- `pi_display/refresh.py`
  - Expose or reuse refresh generation entry points cleanly for export jobs if needed.
- `README.md`
  - Document monthly export workflow, required secrets, and manual execution steps.
- `requirements.txt`
  - Add the chosen rendering dependency for JPG export.

## Task 1: Create the Month-End Gate and Export Window Logic

**Files:**
- Create: `tests/test_monthly_export.py`
- Create: `pi_display/monthly_export.py`

- [ ] **Step 1: Write the failing tests for date gating and export window selection**

```python
from datetime import date

from pi_display.monthly_export import (
    build_export_window,
    is_three_days_before_month_end,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monthly_export.py -k "month_end or export_window" -v`

Expected: FAIL with `ModuleNotFoundError` or missing function import errors for `pi_display.monthly_export`

- [ ] **Step 3: Write the minimal implementation for date gating and export window selection**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange


@dataclass(frozen=True)
class ExportWindow:
    start: date
    end: date
    label: str


def last_day_of_month(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + offset
    return divmod(month_index, 12)[0], divmod(month_index, 12)[1] + 1


def is_three_days_before_month_end(today: date) -> bool:
    return today == last_day_of_month(today) - timedelta(days=3)


def build_export_window(run_date: date) -> ExportWindow:
    end_year, end_month = add_months(run_date.year, run_date.month, 3)
    end = date(end_year, end_month, monthrange(end_year, end_month)[1])
    label = f"{run_date.strftime('%B')}-{end.strftime('%B %Y')}"
    return ExportWindow(start=run_date, end=end, label=label)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_monthly_export.py -k "month_end or export_window" -v`

Expected: PASS for all new month-end and export-window tests

- [ ] **Step 5: Commit**

```bash
git add tests/test_monthly_export.py pi_display/monthly_export.py
git commit -m "feat: add monthly export window logic"
```

## Task 2: Add Event Selection, Exhibition Formatting, and Filenames

**Files:**
- Modify: `tests/test_monthly_export.py`
- Modify: `pi_display/monthly_export.py`

- [ ] **Step 1: Write the failing tests for event filtering, exhibition formatting, and filenames**

```python
from pi_display.monthly_export import (
    build_export_filename,
    format_export_date_lines,
    select_export_events,
)


def test_select_export_events_excludes_classes_and_out_of_window_items():
    items = [
        {"title": "Stage Show", "dateText": "04 Jun 2026", "sortDate": "2026-06-04T00:00:00", "isClass": False},
        {"title": "Workshop", "dateText": "05 Jun 2026", "sortDate": "2026-06-05T00:00:00", "isClass": True},
        {"title": "Future Show", "dateText": "02 Sep 2026", "sortDate": "2026-09-02T00:00:00", "isClass": False},
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


def test_build_export_filename_uses_sortable_slug():
    item = {"title": "Sherlock Holmes and The Sting of the Scorpion", "sortDate": "2026-06-04T00:00:00"}

    assert build_export_filename(item) == "2026-06-04-sherlock-holmes-and-the-sting-of-the-scorpion.jpg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monthly_export.py -k "select_export_events or format_export_date_lines or build_export_filename" -v`

Expected: FAIL with missing function errors

- [ ] **Step 3: Write the minimal implementation for event filtering and export text helpers**

```python
from datetime import datetime
import re


def normalize_export_text(value: str | None) -> str:
    return str(value or "").replace("Ãƒâ€šÃ‚Â£", "£").replace("–", "-").replace("—", "-").strip()


def select_export_events(items: list[dict], start_iso: str, end_iso: str) -> list[dict]:
    start = datetime.fromisoformat(start_iso).date()
    end = datetime.fromisoformat(end_iso).date()
    selected = []
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_monthly_export.py -k "select_export_events or format_export_date_lines or build_export_filename" -v`

Expected: PASS for event selection, exhibition formatting, and filename tests

- [ ] **Step 5: Commit**

```bash
git add tests/test_monthly_export.py pi_display/monthly_export.py
git commit -m "feat: add monthly export event selection helpers"
```

## Task 3: Build the Monthly Slide Renderer and Manifest

**Files:**
- Create: `pi_display/monthly_template.py`
- Modify: `pi_display/monthly_export.py`
- Modify: `tests/test_monthly_export.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing tests for render outputs and manifest contents**

```python
from pathlib import Path

from pi_display.monthly_export import build_manifest, render_monthly_export_pack


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


def test_render_monthly_export_pack_creates_both_ratio_folders(tmp_path: Path):
    items = [
        {
            "title": "Sherlock Holmes",
            "category": "Theatre and Performance",
            "dateText": "04 Jun 2026",
            "startTime": "7:30pm",
            "sortDate": "2026-06-04T00:00:00",
            "imageLocal": "cache/images/example.jpg",
            "qrLocal": "cache/qr/example.png",
            "meta": [],
            "isClass": False,
        }
    ]

    render_monthly_export_pack(root_dir=tmp_path, items=items, window_label="May-August 2026")

    assert (tmp_path / "16x9").exists()
    assert (tmp_path / "4x3").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monthly_export.py -k "manifest or render_monthly_export_pack" -v`

Expected: FAIL with missing renderer or manifest function errors

- [ ] **Step 3: Write the minimal implementation for rendering and manifest generation**

```python
from pathlib import Path
import json
import zipfile

from PIL import Image, ImageDraw, ImageFont


def build_manifest(window_label: str, selected_count: int, generated_count: int, warnings: list[dict]) -> dict:
    return {
        "windowLabel": window_label,
        "selectedCount": selected_count,
        "generatedCount": generated_count,
        "warnings": warnings,
    }


def ensure_ratio_dirs(root_dir: Path) -> tuple[Path, Path]:
    wide = root_dir / "16x9"
    standard = root_dir / "4x3"
    wide.mkdir(parents=True, exist_ok=True)
    standard.mkdir(parents=True, exist_ok=True)
    return wide, standard


def render_slide_jpg(item: dict, ratio: str, output_file: Path, root_dir: Path) -> None:
    canvas_size = (1600, 900) if ratio == "16x9" else (1200, 900)
    image = Image.new("RGB", canvas_size, "#f4eee6")
    draw = ImageDraw.Draw(image)

    # The real implementation should:
    # 1. paste the cached event artwork into the left panel
    # 2. paint the approved right-hand panel background
    # 3. draw category, title, and meta/date lines using the approved spacing
    # 4. paste the cached QR image at the approved larger size
    # 5. save as high-quality JPG

    draw.text((60, 60), item["title"], fill="#1f1714")
    image.save(output_file, format="JPEG", quality=95, subsampling=0)


def render_monthly_export_pack(root_dir: Path, items: list[dict], window_label: str) -> dict:
    wide_dir, standard_dir = ensure_ratio_dirs(Path(root_dir))
    generated_files: list[Path] = []
    warnings: list[dict] = []

    for item in items:
        filename = build_export_filename(item)
        for ratio, target_dir in (("16x9", wide_dir), ("4x3", standard_dir)):
            output_file = target_dir / filename
            render_slide_jpg(item=item, ratio=ratio, output_file=output_file, root_dir=Path(root_dir))
            generated_files.append(output_file)

    manifest = build_manifest(
        window_label=window_label,
        selected_count=len(items),
        generated_count=len(generated_files),
        warnings=warnings,
    )
    (Path(root_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def create_export_zip(root_dir: Path, zip_name: str) -> Path:
    zip_path = Path(root_dir) / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in Path(root_dir).rglob("*"):
            if file_path == zip_path or file_path.is_dir():
                continue
            archive.write(file_path, file_path.relative_to(root_dir))
    return zip_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_monthly_export.py -k "manifest or render_monthly_export_pack" -v`

Expected: PASS for manifest and folder-creation tests

- [ ] **Step 5: Commit**

```bash
git add tests/test_monthly_export.py pi_display/monthly_export.py pi_display/monthly_template.py requirements.txt
git commit -m "feat: add monthly export renderer scaffolding"
```

## Task 4: Wire the End-to-End Export Command

**Files:**
- Modify: `pi_display/monthly_export.py`
- Modify: `pi_display/config.py`
- Modify: `tests/test_monthly_export.py`

- [ ] **Step 1: Write the failing tests for the high-level export run**

```python
from pathlib import Path

from pi_display.monthly_export import run_monthly_export


def test_run_monthly_export_writes_manifest_and_zip(tmp_path: Path):
    payload = {
        "items": [
            {
                "title": "Sherlock Holmes",
                "category": "Theatre and Performance",
                "dateText": "04 Jun 2026",
                "startTime": "7:30pm",
                "sortDate": "2026-06-04T00:00:00",
                "imageLocal": "cache/images/example.jpg",
                "qrLocal": "cache/qr/example.png",
                "meta": [],
                "isClass": False,
            }
        ]
    }

    result = run_monthly_export(root_dir=tmp_path, payload=payload, run_date_iso="2026-05-28")

    assert result["zipPath"].endswith(".zip")
    assert (tmp_path / "manifest.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monthly_export.py -k "run_monthly_export" -v`

Expected: FAIL with missing function errors

- [ ] **Step 3: Write the minimal implementation for the orchestration function**

```python
def run_monthly_export(root_dir: Path, payload: dict, run_date_iso: str) -> dict:
    run_date = datetime.fromisoformat(run_date_iso).date()
    window = build_export_window(run_date)
    export_dir = Path(root_dir)
    items = select_export_events(
        payload.get("items", []),
        start_iso=window.start.isoformat(),
        end_iso=window.end.isoformat(),
    )
    manifest = render_monthly_export_pack(export_dir, items, window.label)
    zip_path = create_export_zip(export_dir, f"acw-monthly-slides-{run_date.strftime('%Y-%m')}.zip")
    return {
        "windowLabel": window.label,
        "selectedCount": manifest["selectedCount"],
        "generatedCount": manifest["generatedCount"],
        "zipPath": str(zip_path),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_monthly_export.py -k "run_monthly_export" -v`

Expected: PASS for the high-level export run test

- [ ] **Step 5: Commit**

```bash
git add tests/test_monthly_export.py pi_display/monthly_export.py pi_display/config.py
git commit -m "feat: add monthly export orchestration"
```

## Task 5: Add the Scheduled GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/monthly-slide-export.yml`
- Create: `scripts/send_monthly_export_email.py`
- Modify: `tests/test_monthly_export.py` only if workflow-adjacent gate logic still needs unit coverage

- [ ] **Step 1: Write the workflow file with manual dispatch and daily schedule**

```yaml
name: Monthly Slide Export Email

on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * *"

permissions:
  contents: read

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: python -m pip install -r requirements.txt

      - name: Evaluate month-end gate
        id: gate
        run: python - <<'PY'
from datetime import date
from pi_display.monthly_export import is_three_days_before_month_end
today = date.today()
print(f"run_export={'true' if is_three_days_before_month_end(today) else 'false'}")
PY >> $GITHUB_OUTPUT

      - name: Stop when outside export window
        if: github.event_name != 'workflow_dispatch' && steps.gate.outputs.run_export != 'true'
        run: echo "Not three days before month-end. Exiting."

      - name: Run monthly export
        if: github.event_name == 'workflow_dispatch' || steps.gate.outputs.run_export == 'true'
        run: python -m pi_display.monthly_export

      - name: Upload export artifact
        if: github.event_name == 'workflow_dispatch' || steps.gate.outputs.run_export == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: monthly-slide-export
          path: output/monthly-export/
```

- [ ] **Step 2: Run local tests to confirm the workflow depends on passing logic**

Run: `pytest tests/test_monthly_export.py -v`

Expected: PASS for all monthly export tests before relying on the workflow

- [ ] **Step 3: Add the email delivery step with secrets-backed configuration**

```yaml
      - name: Send email with download link
        if: github.event_name == 'workflow_dispatch' || steps.gate.outputs.run_export == 'true'
        env:
          EXPORT_EMAIL_TO: ${{ secrets.EXPORT_EMAIL_TO }}
          EXPORT_EMAIL_FROM: ${{ secrets.EXPORT_EMAIL_FROM }}
          EXPORT_SMTP_HOST: ${{ secrets.EXPORT_SMTP_HOST }}
          EXPORT_SMTP_PORT: ${{ secrets.EXPORT_SMTP_PORT }}
          EXPORT_SMTP_USERNAME: ${{ secrets.EXPORT_SMTP_USERNAME }}
          EXPORT_SMTP_PASSWORD: ${{ secrets.EXPORT_SMTP_PASSWORD }}
        run: python scripts/send_monthly_export_email.py
```

- [ ] **Step 3a: Add the SMTP email helper script**

```python
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def main() -> None:
    manifest = json.loads(Path("output/monthly-export/manifest.json").read_text(encoding="utf-8"))
    artifact_url = os.environ["EXPORT_DOWNLOAD_URL"]

    message = EmailMessage()
    message["Subject"] = f"ACW monthly slide export: {manifest['windowLabel']}"
    message["From"] = os.environ["EXPORT_EMAIL_FROM"]
    message["To"] = os.environ["EXPORT_EMAIL_TO"]
    message.set_content(
        f"Monthly slide export ready for {manifest['windowLabel']}.\n"
        f"Slides generated: {manifest['generatedCount']}.\n"
        f"Download: {artifact_url}\n"
    )

    with smtplib.SMTP(os.environ["EXPORT_SMTP_HOST"], int(os.environ["EXPORT_SMTP_PORT"])) as smtp:
        smtp.starttls()
        smtp.login(os.environ["EXPORT_SMTP_USERNAME"], os.environ["EXPORT_SMTP_PASSWORD"])
        smtp.send_message(message)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Re-run tests to verify code remains green after workflow wiring**

Run: `pytest tests/test_monthly_export.py -v`

Expected: PASS for all monthly export tests

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/monthly-slide-export.yml scripts/send_monthly_export_email.py tests/test_monthly_export.py
git commit -m "feat: add monthly export workflow"
```

## Task 6: Document the Operator Flow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add README documentation for the monthly export workflow**

```markdown
### Monthly slide export email

The repository includes a scheduled GitHub Actions workflow that prepares a monthly ZIP of upcoming event slides in:

- `16:9`
- `4:3`

The workflow:

- runs daily
- exits unless it is three days before month-end
- supports manual runs through `workflow_dispatch`
- uploads an export artifact
- emails a download link to the configured recipient

Required secrets:

- `EXPORT_EMAIL_TO`
- `EXPORT_EMAIL_FROM`
- `EXPORT_SMTP_HOST`
- `EXPORT_SMTP_PORT`
- `EXPORT_SMTP_USERNAME`
- `EXPORT_SMTP_PASSWORD`
- `EXPORT_DOWNLOAD_URL` if the email step expects the workflow to inject a resolved artifact link
```

- [ ] **Step 2: Run tests to ensure documentation changes did not require code updates**

Run: `pytest tests/test_monthly_export.py -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document monthly slide export workflow"
```

## Final Verification

- [ ] **Step 1: Run the focused monthly export test suite**

Run: `pytest tests/test_monthly_export.py -v`

Expected: PASS

- [ ] **Step 2: Run the existing publisher and scraper tests to catch regressions**

Run: `pytest tests/test_publisher.py tests/test_scraper.py -v`

Expected: PASS

- [ ] **Step 3: Smoke-test a manual export locally**

Run: `python -m pi_display.monthly_export`

Expected: writes `output/monthly-export/`, `manifest.json`, `16x9/`, `4x3/`, and a ZIP archive

- [ ] **Step 4: Commit the final integrated state**

```bash
git add .github/workflows/monthly-slide-export.yml README.md pi_display/monthly_export.py pi_display/monthly_template.py scripts/send_monthly_export_email.py tests/test_monthly_export.py requirements.txt
git commit -m "feat: add monthly slide export email workflow"
```
