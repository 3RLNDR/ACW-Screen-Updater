# Monthly Export Typography Refinement Design

Date: 2026-06-03

## Goal

Refine the monthly export slide design from the current stable renderer toward a more branded, structured look without losing readability or reintroducing title truncation.

The approved direction is based on the existing split-layout export and the browser mockup option `C` ("Branded Utility"), with a typography update:

- `Montserrat Bold` for category labels
- `Montserrat SemiBold` for event titles
- `Arial` for metadata and supporting utility text

This design must work in both `16:9` and `4:3`, with a specific verification pass for `4:3` text overlay and image crop pressure before the implementation is considered complete.

## Current Context

The current renderer already improved several structural issues:

- exhibition date/note overlap has been fixed
- long titles are less likely to ellipsize
- the slide family is more visually consistent than before

The remaining approved design work is not a full redesign. It is a targeted refinement of the current export system:

- keep the existing image-plus-panel composition
- keep the current QR placement model as a general pattern
- refine the typography hierarchy so the slides feel more intentionally branded
- avoid reopening the previous "preset drift" problem

## Approved Direction

### Visual Base

Use the current warm split-layout approach as the base rather than the later bold block-colour exploration.

That means:

- large event artwork remains the dominant visual element
- the information panel remains visually separated from the image
- category, title, and metadata retain a clear hierarchy
- the design should feel more system-like and branded, but not loudly posterised

### Typography

Typography is the primary refinement area for this phase.

Approved type system:

- Category: `Montserrat Bold`
- Title: `Montserrat SemiBold`
- Metadata and utility copy: `Arial`

Intended effect:

- category labels feel crisp and branded
- titles feel modern and structured rather than literary/editorial
- utility information remains highly legible and operational

### Hierarchy

The approved hierarchy is closest to mockup option `C`:

- category presented as a compact branded label
- title as the main focal text block
- metadata visually secondary but still easy to scan

This should feel more structured than option `A`, and less theatrical than option `B`.

## Layout Rules

### 16:9

For `16:9`, preserve the current overall composition:

- image area remains dominant
- panel remains a stable text container
- title may wrap to multiple lines when needed
- QR stays anchored low in the panel

Typography changes must not force the date block, QR, or note lines into collisions.

### 4:3

`4:3` is an explicit follow-up concern, not an afterthought.

Implementation must include a focused review of:

- title wrapping pressure in the narrower panel
- category-label width and chip fit
- interaction between title depth and metadata placement
- artwork crop quality when the image area narrows
- whether any titles that fit comfortably in `16:9` become visually cramped in `4:3`

The `4:3` version does not need a different visual language, but it may need stricter sizing rules or spacing adjustments to preserve the same hierarchy cleanly.

## Font Strategy

Montserrat should not be assumed to exist on the host machine.

Design requirement:

- bundle the required Montserrat font files with the project, or otherwise provide them deterministically to the renderer
- the render path must use those assets intentionally rather than depending on system-installed fonts

This prevents environment-specific differences between local runs, GitHub Actions, and other export environments.

## Title-Fit Requirements

Switching from `Georgia` to `Montserrat` changes width behavior, so title fitting must be treated as part of the design, not just a technical detail.

Requirements:

- titles should prefer wrapping over ellipsis wherever the layout can still remain balanced
- title sizing logic must be recalibrated for Montserrat metrics
- category/title combinations must be validated against known problem cases such as:
  - `Summer Craft & Makers Fair`
  - `A Good Company of Musick: Royal Northern Sinfonia with Ben Lunn`
  - long exhibition titles and mixed-case special-event names

Ellipsis may still exist as a final safety guard, but it should no longer be the normal outcome for titles that can reasonably fit with better sizing or wrapping.

## Renderer Expectations

The renderer should continue to be driven by an explicit spec rather than hidden, font-specific assumptions.

That means the render spec should remain responsible for values such as:

- font family selection
- font size
- title box height
- line-height assumptions
- metadata offsets

This keeps the rendering behavior inspectable and testable when typography changes again later.

## Testing And Verification

Implementation should verify both logic and output:

- unit coverage for title-fit rules and render-spec generation
- regenerated sample exports for representative `16:9` cases
- regenerated sample exports for representative `4:3` cases
- visual checks for at least one short title, one medium title, one long title, and one exhibition case

Success criteria:

- no obvious title ellipsis on approved-fit cases
- no date/title/QR collisions
- typography feels closer to the approved mockup direction
- `4:3` remains readable and visually balanced

## Out Of Scope

The following are not part of this design phase:

- a full colour-system redesign
- rethinking the whole slide composition
- replacing Arial metadata styling with a different utility family
- introducing category-specific visual presets again

## Implementation Notes

The likely implementation path is:

1. update the approved mockup assumptions into the renderer spec
2. introduce deterministic Montserrat font usage
3. recalibrate title-fit and wrapping logic for Montserrat
4. verify `16:9`
5. perform a dedicated `4:3` text-overlay and crop review

## Review Checklist

- approved visual base is the pre-block-colour direction, not the later bold-block detour
- approved typography split is explicit: Montserrat for category/title, Arial for utility text
- `4:3` review is a required part of implementation, not a nice-to-have
- title-fit recalibration is included as part of the design itself
