# Monthly Slide Export Email Design

## Summary

Add a scheduled GitHub Actions workflow that prepares a monthly export pack of upcoming event slides and emails a download link to a ZIP archive. The archive will contain two JPG sets for the next three months of events:

- `16:9`
- `4:3`

The export slides will use the approved monthly-pack layout direction validated during mockup review.

## Goal

Provide a dependable monthly handoff email, sent three days before month-end, containing a download link to a ZIP of high-quality JPG slide exports for the next three months.

## Non-Goals

- editing slide layouts in the dashboard
- generating PDFs in this feature
- sending large ZIP files as direct email attachments
- adding classes and workshops by default
- replacing the live fullscreen display

## Why This Approach

The GitHub Action path is the best fit for this feature because:

- it already exists in this repository as an accepted automation pattern
- monthly scheduling is easy to express with GitHub Actions cron plus a date gate
- the output is static and reproducible
- a ZIP download avoids email attachment size limits
- the export pipeline can reuse the existing stored event data, artwork, and QR assets

## User Experience

Each month, three days before the end of the month, the recipient receives an email that:

- states the export window covered
- summarizes how many slides were generated
- links to a ZIP download

The ZIP contains:

- `/16x9/*.jpg`
- `/4x3/*.jpg`

Each filename should sort predictably and make the event easy to identify, for example:

```text
16x9/2026-06-04-sherlock-holmes-and-the-sting-of-the-scorpion.jpg
4x3/2026-06-04-sherlock-holmes-and-the-sting-of-the-scorpion.jpg
```

## Export Window

The monthly run should export events from the run date through the end of the third following month window covered by the pack.

For example:

- if the workflow runs on `2026-05-28`, the pack should cover late May plus June, July, and August 2026 events that fall within that forward-looking three-month pack window

Implementation detail:

- the exact date filtering logic should be explicit in code and tested
- the subject/body text should name the covered months clearly

## Event Selection Rules

The export job should:

- use the stored event data payload as the source of truth
- exclude classes and workshops by default
- include only events that have enough data to render a complete slide
- prefer stored local artwork rather than remote artwork URLs
- prefer stored local QR codes rather than generating new ones during export

If an event is missing a required asset:

- missing image: fall back to the existing generated poster-style fallback artwork pattern used by the app
- missing QR code but valid event URL exists: generate or recover a QR as part of the export pipeline if feasible
- missing both link and QR source: omit the QR area and mark the run output summary accordingly

## Slide Layout Contract

The approved export layout is:

- left side: full event artwork image
- right side: category, title, date/meta block, and large QR code

The validated content rules are:

- no venue label
- no pack label
- no live-display chrome
- no descriptive helper copy
- no dark overlay band over the image
- no detail tags/pills in the final export version

The validated typography/content rules are:

- category on the right-hand panel
- title below category with reduced vertical gap to the meta line
- enlarged meta line relative to the earlier mockup
- larger QR code than the initial mockup revision

## Exhibition Rules

Exhibitions should follow the same date treatment used in the live fullscreen display:

- the primary export date line should show the exhibition range when available
- the secondary note should show `Open until <dateText>` when appropriate

This must be derived from the same logic used by the live display so the export and screen do not diverge.

## Ratios and Rendering

Each selected event should generate:

- one `16:9` JPG
- one `4:3` JPG

Requirements:

- high-quality JPG output
- consistent composition across both ratios
- proportional resizing, not a separately redesigned template
- predictable safe areas so long titles remain readable

The `4:3` version should preserve the same visual language while adjusting panel proportions and QR placement to fit the narrower frame.

## Output Structure

The workflow should write build artifacts into a generated export directory with a structure similar to:

```text
output/monthly-export/
  manifest.json
  16x9/
    *.jpg
  4x3/
    *.jpg
  acw-monthly-slides-2026-05.zip
```

`manifest.json` should capture:

- run timestamp
- covered date window
- selected event count
- generated file count
- omitted events and reasons

## Delivery Flow

Recommended delivery flow:

1. Refresh/generate the latest static event data.
2. Build both aspect-ratio slide sets.
3. Create a ZIP archive.
4. Upload the ZIP as a workflow artifact or equivalent downloadable asset.
5. Send an email containing:
   - pack summary
   - covered months
   - slide count
   - download link

This keeps the email small and avoids attachment failures.

## Scheduling

GitHub Actions does support scheduled runs, but cron alone cannot directly express "three days before month-end" in a reliable month-aware way. The workflow should therefore:

- run daily on a lightweight schedule
- exit early unless the current date is exactly three days before the final day of the month

This gives predictable behaviour without needing external schedulers.

The workflow should also support:

- `workflow_dispatch` for manual test runs

## Email Requirements

The email content should be brief and operational:

- subject naming the covered pack period
- one short summary paragraph
- download link
- optional list of warnings if events were skipped or fallbacks were used

The recipient address and any mail credentials must come from GitHub secrets or repository variables, never committed configuration.

## Architecture

### Data source

Reuse the existing generated event payload rather than scraping separately inside the export renderer.

### Export renderer

Add a dedicated renderer for monthly export slides instead of trying to screenshot the live fullscreen page. This avoids:

- browser automation fragility
- layout drift from live-screen-only elements
- difficulty producing exact `16:9` and `4:3` outputs

The renderer should take normalized event records and produce deterministic JPG files.

### Workflow orchestration

Add a separate GitHub workflow rather than overloading the Pages deploy workflow. This keeps:

- deployment concerns separate from delivery concerns
- logs easier to read
- failures easier to diagnose

## Error Handling

The workflow should fail clearly when:

- the base data generation fails
- the renderer cannot produce output folders
- ZIP creation fails
- email delivery fails

The workflow should not fail the entire run for one bad event if the rest can still export. Instead:

- skip the bad event
- record the reason in `manifest.json`
- include a warning in the email summary

## Testing Strategy

The implementation should be backed by tests for:

- date-window selection
- month-end gate logic
- filename generation
- exhibition date formatting
- omission/fallback behaviour for missing assets
- manifest generation

If the renderer is template-driven, tests should also verify:

- both aspect ratios are produced
- expected text fields appear in the rendered intermediate template data

## Files and Responsibilities

Expected areas of change:

- `.github/workflows/`
  - new scheduled monthly export workflow
- `pi_display/` or a new export-focused module area
  - selection logic
  - rendering logic
  - ZIP manifest/output helpers
- `tests/`
  - date selection, formatting, renderer, manifest, and workflow-adjacent unit tests
- `README.md`
  - operator documentation for manual runs and configuration

## Open Implementation Decisions

These should be resolved during planning, not by changing the approved feature scope:

- exact artifact hosting mechanism for the email link
- exact rendering technology for JPG generation
- whether QR fallback generation is in scope for v1 or deferred behind a warning-only behaviour

## Recommendation

Implement v1 as:

- a dedicated GitHub Actions workflow
- daily scheduled trigger with a three-days-before-month-end gate
- deterministic local renderer for the approved monthly-pack slide layout
- ZIP artifact upload
- email containing a download link and warnings summary

This is the simplest version that satisfies the feature request while keeping operational risk low.
