# Monthly Export Typography Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the monthly export renderer to use the approved branded typography direction with deterministic Montserrat title/category styling, Arial utility text, QR helper-copy rules, and verified `16:9` plus `4:3` output.

**Architecture:** Keep the existing monthly export pipeline and render-spec approach, but expand the spec so typography and QR helper-copy are explicit renderer inputs rather than implicit script assumptions. Add deterministic font asset resolution, recalibrate title-fit logic for Montserrat, and verify the result with focused unit tests plus regenerated visual output in both aspect ratios.

**Tech Stack:** Python 3, pytest, PowerShell, System.Drawing, bundled font assets, existing monthly export pipeline

---

## File Structure

- Create: `assets/fonts/Montserrat-SemiBold.ttf`
  - Bundled title font used by the renderer instead of relying on system-installed fonts.
- Create: `assets/fonts/Montserrat-Bold.ttf`
  - Bundled category-label font used by the renderer instead of relying on system-installed fonts.
- Modify: `pi_display/monthly_export.py`
  - Extend render-spec generation to carry explicit font-family/font-file data, QR helper-copy, lighter cream panel styling, and Montserrat-aware title-fit rules.
- Modify: `scripts/render-monthly-export-slide.ps1`
  - Load private font files, render Montserrat for title/category, keep Arial for utility text, and draw QR helper copy aligned above the QR block.
- Modify: `tests/test_monthly_export.py`
  - Add focused tests for font selection, free-event QR helper-copy, Montserrat title-fit behavior, and `4:3` spacing expectations.
- Modify: `.gitignore`
  - Ignore `.superpowers/` brainstorming files created during preview work.

## Task 1: Bundle Font Assets And Ignore Preview Artifacts

**Files:**
- Create: `assets/fonts/Montserrat-SemiBold.ttf`
- Create: `assets/fonts/Montserrat-Bold.ttf`
- Modify: `.gitignore`
- Test: `tests/test_monthly_export.py`

- [ ] **Step 1: Add a failing test that expects Montserrat asset paths in the render spec**

```python
def test_build_render_spec_uses_bundled_montserrat_assets():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item=build_render_item(),
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["categoryFontFile"].endswith("assets/fonts/Montserrat-Bold.ttf")
    assert spec["titleFontFile"].endswith("assets/fonts/Montserrat-SemiBold.ttf")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_monthly_export.py::test_build_render_spec_uses_bundled_montserrat_assets -q`
Expected: FAIL with `KeyError` for `categoryFontFile` or `titleFontFile`

- [ ] **Step 3: Add the font files and ignore brainstorm output**

Add these files to the repository:

- `assets/fonts/Montserrat-SemiBold.ttf`
- `assets/fonts/Montserrat-Bold.ttf`

Update `.gitignore`:

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
__pycache__/
.tmp/
.superpowers/
```

- [ ] **Step 4: Add minimal render-spec support for font file paths**

Update `pi_display/monthly_export.py`:

```python
FONT_ASSETS = {
    "category": "assets/fonts/Montserrat-Bold.ttf",
    "title": "assets/fonts/Montserrat-SemiBold.ttf",
}
```

Inside `build_render_spec(...)`, add:

```python
        "categoryFontFile": str((project_root / FONT_ASSETS["category"]).resolve()),
        "titleFontFile": str((project_root / FONT_ASSETS["title"]).resolve()),
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_monthly_export.py::test_build_render_spec_uses_bundled_montserrat_assets -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add .gitignore assets/fonts/Montserrat-SemiBold.ttf assets/fonts/Montserrat-Bold.ttf pi_display/monthly_export.py tests/test_monthly_export.py
git commit -m "feat: bundle montserrat assets for monthly export"
```

## Task 2: Encode The Approved Typography And QR Helper-Copy In The Render Spec

**Files:**
- Modify: `pi_display/monthly_export.py`
- Modify: `tests/test_monthly_export.py`

- [ ] **Step 1: Add failing tests for QR helper-copy and approved type split**

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_monthly_export.py -k "qrPrompt or approved_typography_defaults" -q`
Expected: FAIL with missing render-spec keys

- [ ] **Step 3: Add helper functions for free-event detection and QR prompt selection**

In `pi_display/monthly_export.py`, add:

```python
def is_free_event(item: dict) -> bool:
    values = [
        normalize_export_text(item.get("cost")).lower(),
        normalize_export_text(item.get("status")).lower(),
    ]
    return any(value == "free" for value in values)


def get_qr_prompt(item: dict) -> str:
    return "Find out more" if is_free_event(item) else "Scan to book"
```

- [ ] **Step 4: Add the approved typography and QR prompt to the render spec**

Inside `build_render_spec(...)`, add:

```python
        "categoryFontFamily": "Montserrat",
        "titleFontFamily": "Montserrat",
        "metaFontFamily": "Arial",
        "noteFontFamily": "Arial",
        "qrPrompt": get_qr_prompt(item),
        "panelColor": "#fcf5ea",
```

Keep the existing lighter cream direction and continue using the current warm gradient family.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_monthly_export.py -k "qrPrompt or approved_typography_defaults" -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pi_display/monthly_export.py tests/test_monthly_export.py
git commit -m "feat: add approved typography and qr prompt rules"
```

## Task 3: Recalibrate Title-Fit Logic For Montserrat

**Files:**
- Modify: `pi_display/monthly_export.py`
- Modify: `tests/test_monthly_export.py`

- [ ] **Step 1: Add failing tests for Montserrat-aware title-fit behavior**

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_monthly_export.py -k "summer_craft_title or long_music_event" -q`
Expected: FAIL because the current title-fit logic is still calibrated around the old assumptions

- [ ] **Step 3: Replace the old width heuristic with a Montserrat-aware estimator**

In `pi_display/monthly_export.py`, update the estimator logic so it is explicitly based on the approved title family:

```python
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
```

Update `estimate_title_lines(...)` and `build_title_layout(...)` so:

- `Summer Craft & Makers Fair` gets safe two-line room in `16:9`
- long titles shrink earlier
- the line-height and title box remain explicit in the spec

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `python -m pytest tests/test_monthly_export.py -k "summer_craft_title or long_music_event" -q`
Expected: PASS

- [ ] **Step 5: Run the full monthly export test suite**

Run: `python -m pytest tests/test_monthly_export.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pi_display/monthly_export.py tests/test_monthly_export.py
git commit -m "feat: recalibrate monthly export title fitting for montserrat"
```

## Task 4: Update The PowerShell Renderer For Bundled Fonts And QR Prompt Copy

**Files:**
- Modify: `scripts/render-monthly-export-slide.ps1`
- Modify: `tests/test_monthly_export.py`

- [ ] **Step 1: Add a failing test for render-spec fields required by the PowerShell renderer**

```python
def test_build_render_spec_exposes_qr_prompt_and_font_families_for_renderer():
    project_root = Path.cwd()
    output_file = project_root / "out.jpg"

    spec = build_render_spec(
        project_root=project_root,
        item={**build_render_item(), "cost": "Free", "status": "Free"},
        ratio="16x9",
        output_file=output_file,
    )

    assert spec["qrPrompt"] == "Find out more"
    assert spec["titleFontFamily"] == "Montserrat"
    assert spec["metaFontFamily"] == "Arial"
```

- [ ] **Step 2: Run the test to verify it fails if Task 2 has not been completed, or skip if already green**

Run: `python -m pytest tests/test_monthly_export.py::test_build_render_spec_exposes_qr_prompt_and_font_families_for_renderer -q`
Expected: PASS only after Task 2 is complete

- [ ] **Step 3: Update the renderer to load private font files and draw the approved type system**

In `scripts/render-monthly-export-slide.ps1`:

```powershell
$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile([string]$spec.categoryFontFile)
$fontCollection.AddFontFile([string]$spec.titleFontFile)

$categoryFamily = $fontCollection.Families | Where-Object { $_.Name -eq [string]$spec.categoryFontFamily } | Select-Object -First 1
$titleFamily = $fontCollection.Families | Where-Object { $_.Name -eq [string]$spec.titleFontFamily } | Select-Object -First 1

$categoryFont = New-Object System.Drawing.Font($categoryFamily, [float]$spec.categoryFontSize, [System.Drawing.FontStyle]::Bold)
$titleFont = New-Object System.Drawing.Font($titleFamily, [float]$spec.titleFontSize, [System.Drawing.FontStyle]::Regular)
$metaFont = New-Object System.Drawing.Font([string]$spec.metaFontFamily, [float]$spec.metaFontSize, [System.Drawing.FontStyle]::Bold)
$noteFont = New-Object System.Drawing.Font([string]$spec.noteFontFamily, [float]$spec.noteFontSize, [System.Drawing.FontStyle]::Regular)
```

Also draw the QR helper-copy above the QR:

```powershell
$qrPromptFont = New-Object System.Drawing.Font([string]$spec.metaFontFamily, 15.0, [System.Drawing.FontStyle]::Bold)
$graphics.DrawString([string]$spec.qrPrompt, $qrPromptFont, $inkBrush, [float]$spec.qrX, [float]($spec.qrY - 28))
```

Keep the helper-copy aligned to the QR block’s left edge.

- [ ] **Step 4: Dispose of all new font resources**

Make sure these are disposed in the `finally` section:

```powershell
$categoryFont.Dispose()
$titleFont.Dispose()
$metaFont.Dispose()
$noteFont.Dispose()
$qrPromptFont.Dispose()
$fontCollection.Dispose()
```

- [ ] **Step 5: Run the full monthly export test suite**

Run: `python -m pytest tests/test_monthly_export.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/render-monthly-export-slide.ps1 tests/test_monthly_export.py
git commit -m "feat: render monthly export typography with bundled montserrat"
```

## Task 5: Regenerate Output And Perform The Required 16:9 / 4:3 Review

**Files:**
- Modify: `output/monthly-export/manifest.json`
- Modify: `output/monthly-export/16x9/*.jpg`
- Modify: `output/monthly-export/4x3/*.jpg`

- [ ] **Step 1: Run the exporter to regenerate the pack**

Run: `python -m pi_display.monthly_export`
Expected: fresh `output/monthly-export/manifest.json`, JPGs, and ZIP file

- [ ] **Step 2: Inspect representative `16:9` outputs**

Review these regenerated files:

- `output/monthly-export/16x9/2026-07-18-summer-craft-makers-fair.jpg`
- `output/monthly-export/16x9/2026-06-17-a-good-company-of-musick-royal-northern-sinfonia-with-ben-lunn.jpg`
- `output/monthly-export/16x9/2026-06-06-broken.jpg`
- `output/monthly-export/16x9/2026-06-03-song-sung-blue.jpg`

Confirm:

- title uses Montserrat
- category uses Montserrat
- metadata remains Arial
- free event uses `Find out more`
- paid event uses `Scan to book`
- no obvious title ellipsis on approved-fit cases

- [ ] **Step 3: Inspect representative `4:3` outputs**

Review these regenerated files:

- `output/monthly-export/4x3/2026-07-18-summer-craft-makers-fair.jpg`
- `output/monthly-export/4x3/2026-06-17-a-good-company-of-musick-royal-northern-sinfonia-with-ben-lunn.jpg`
- `output/monthly-export/4x3/2026-06-06-broken.jpg`
- `output/monthly-export/4x3/2026-06-03-song-sung-blue.jpg`

Confirm:

- title wrapping still feels balanced in the narrower panel
- category chip still fits cleanly
- metadata does not collide with title or QR
- artwork crop quality remains acceptable

- [ ] **Step 4: If `4:3` review reveals pressure, add the minimal ratio-specific spacing adjustment**

If the review shows collisions or cramped layout, update only the ratio-specific spacing values in `pi_display/monthly_template.py` or `pi_display/monthly_export.py` that control:

- `title_width`
- `meta_y`
- `qr_y`
- `qr_size`

Do not redesign the composition. Make the smallest adjustment that resolves the pressure.

- [ ] **Step 5: Re-run the exporter after any spacing adjustment**

Run: `python -m pi_display.monthly_export`
Expected: refreshed JPG output reflecting the final ratio-specific tuning

- [ ] **Step 6: Commit**

```bash
git add output/monthly-export/manifest.json output/monthly-export/16x9 output/monthly-export/4x3
git commit -m "chore: regenerate monthly export previews"
```

## Self-Review

- Spec coverage: the plan covers deterministic Montserrat usage, approved typography split, lighter cream panel preservation, QR helper-copy derived from free/paid state, title-fit recalibration, and the required `4:3` verification pass.
- Placeholder scan: no `TODO`, `TBD`, or generic “handle it later” instructions remain; each task includes exact files, tests, commands, and expected outcomes.
- Type consistency: the plan consistently uses `categoryFontFile`, `titleFontFile`, `categoryFontFamily`, `titleFontFamily`, `metaFontFamily`, and `qrPrompt` across renderer and test tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-03-monthly-export-typography-refinement.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
