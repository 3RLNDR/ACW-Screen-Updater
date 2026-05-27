# Pi Hosting And Video Slide Design

## Summary

This project will move from a Windows-first, PowerShell-centered deployment model to a Raspberry Pi-hosted production setup. The Pi will host the dashboard and fullscreen display, run the event refresh/build pipeline on a schedule, store local promo video assets, and serve a generated slideshow that supports both event slides and a new video slide type.

Version 1 also adds a lightweight web UI that allows operators to associate hosted video files with specific scraped event entries. When an event has an associated video, the fullscreen rotation should play the video first and then advance to the existing event slide with booking QR code and event details.

## Goals

- Make the Raspberry Pi the primary production host for the display system.
- Keep the browser display webpage-based, simple, and reliable.
- Support locally hosted video files as a first-class slideshow item.
- Allow operators to associate a video with a specific event through a web UI.
- Generate a slideshow sequence that plays `video -> event` when a mapping exists.
- Preserve a local development path for testing, even though it is no longer the primary deployment target.

## Non-Goals

- No YouTube scraping or embedded third-party video support.
- No full CMS or advanced media library management.
- No browser-based video editing, transcoding, or compression.
- No multi-screen targeting or role-based admin system in v1.
- No requirement to preserve PowerShell as the production refresh engine.

## Architecture

The Raspberry Pi runs the full production setup:

- a small local web application or service
- a scheduled refresh/build job
- a static asset host for the dashboard, fullscreen frontend, images, and video files
- local persistence for uploaded videos and event-to-video mappings

The frontend remains static-browser oriented. It reads generated JSON outputs and renders the dashboard and fullscreen display in the browser. The Pi-side service is responsible for gathering source data, storing operator-managed data, and publishing the generated outputs the frontend consumes.

This creates three clear layers:

1. Source layer: scraped event data from the Sunderland Culture site
2. Management layer: uploaded video assets and event associations stored on the Pi
3. Presentation layer: generated slideshow data plus static frontend files served to the browser

## Runtime Model

The Pi system should behave as a hybrid publisher:

- a scheduled job refreshes event data on a fixed interval
- the job rebuilds generated output files used by the frontend
- the web app exposes admin endpoints and dashboard pages for managing videos and associations
- the browser display reads the generated files rather than making the fullscreen player depend on complex live backend logic

This keeps the fullscreen screen resilient and simple while still allowing dynamic management through the dashboard.

## Data Model

### Scraped Events

Scraped events remain refreshable source data. They should continue to include the existing core fields such as title, category, date, time, price, link, image, and QR code path.

Each event should also have a stable generated identifier suitable for association. That identifier can be derived from stable event properties, but it must be deterministic across refreshes whenever the source event remains the same.

### Video Assets

Video assets are stored locally on the Pi filesystem and tracked in local persistence. Each video record should include fields such as:

- `id`
- `title`
- `filename`
- `storagePath`
- `posterPath` if available
- `mimeType`
- `durationSeconds` if known
- `enabled`
- `createdAt`
- `updatedAt`

### Event Video Associations

Associations connect one event to zero or one preferred video for v1. Each association should include:

- `eventId`
- `videoId`
- `enabled`
- `createdAt`
- `updatedAt`

V1 assumes one active video per event. If future needs change, the model can be extended to support multiple videos and ordering without redesigning the frontend slide type.

### Generated Slide Output

The refresh/build pipeline should generate a unified slideshow dataset for the fullscreen frontend. Each slide entry should have a `type` field:

- `event`
- `video`

Video slides should include enough metadata for native browser playback:

- `type`
- `id`
- `title`
- `src`
- `poster`
- `durationSeconds` or playback policy fields
- `eventId` when paired

Event slides should preserve the existing event rendering data and include the associated `eventId`.

## Storage

SQLite is the recommended local persistence layer on the Pi. It is lightweight, reliable, easy to back up, and a good fit for a single-device admin workflow.

SQLite should store:

- video asset records
- event-to-video associations
- optional refresh bookkeeping if useful

The filesystem should store:

- uploaded video files
- optional poster images or derived thumbnails
- generated JSON outputs
- cached event images and QR codes

## Admin UI

The dashboard gains a lightweight management area for video association. It does not need to be a full admin application in v1.

Required operator capabilities:

- view current scraped events
- view uploaded video assets
- upload a new video file to the Pi
- associate a video with a specific event
- remove or change an existing association
- see whether an event currently has a linked video

Nice-to-have but not required in v1:

- playback preview inside the dashboard
- drag-and-drop upload polish
- thumbnail generation
- bulk reassignment tools

## Fullscreen Playback Behavior

The fullscreen display shifts from an event-only carousel to a slide renderer.

Rules for v1:

- if an event has an associated enabled video, render a `video` slide immediately before that event slide
- once video playback completes or reaches the configured playback limit, advance automatically to the paired event slide
- if an event has no video, render only the existing event slide
- the event slide continues to show the QR code and booking details

Video playback should use a native HTML `<video>` element with muted autoplay by default for maximum signage reliability.

The fullscreen player must explicitly handle:

- loading state for video assets
- playback end transition
- playback timeout or configured maximum duration
- fallback if a video file fails to load

On video failure, the player should skip the video and continue directly to the event slide rather than stalling the rotation.

## Refresh And Publish Flow

The Pi refresh/build flow should run on a schedule and perform these steps:

1. Fetch and parse the source event listing and detail pages
2. Normalize event data and supporting image/QR assets
3. Load saved video and association data from SQLite
4. Build the generated slideshow model by pairing videos with matching events
5. Write the output JSON files consumed by the frontend
6. Leave the static frontend and media assets ready to be served by the Pi web host

The admin UI should not have to rebuild the entire frontend bundle when changing an association. At minimum, it should trigger regeneration of the generated data outputs so the fullscreen display can pick up changes on its next refresh cycle.

## Deployment Direction

The Raspberry Pi is the primary production environment.

The current GitHub Pages deployment may remain useful as a fallback or preview environment, but it is no longer the main design target for this feature set.

The current Windows local server path remains useful for testing during transition, but it should be documented as non-production and should not dictate the final architecture.

## Testing Strategy

The implementation should be validated at three levels:

- refresh/build validation: event scraping, output generation, and association resolution
- admin UI validation: upload, associate, replace, and remove mapping flows
- fullscreen playback validation: mixed slide sequencing, autoplay behavior, and failure fallback

Key scenarios:

- event without video
- event with valid video
- video file missing or unreadable
- association points to an unavailable event after refresh
- event data refresh keeps stable association when the event still exists

## Risks

- Event identifiers may drift if the source site changes structure or content formatting.
- Video files can consume significant storage on the Pi if left unmanaged.
- Browser autoplay policy still favors muted playback, so audible autoplay should not be assumed.
- Long-running refresh or media operations should not block the display frontend.

## Recommended Implementation Order

1. Establish the Pi-native hosting and refresh architecture
2. Introduce local persistence for video assets and associations
3. Add upload and association UI to the dashboard
4. Generate unified slideshow data with `video` and `event` slide types
5. Update fullscreen playback to support video-first paired rendering
6. Retire or reduce Windows-first assumptions in documentation and runtime defaults

## Open Decisions Resolved In This Design

- Production host: Raspberry Pi
- Deployment style: hybrid publisher with generated frontend data
- Video source: local hosted files on the Pi
- Video pairing model: operator-managed event-to-video association in the web UI
- Persistence: SQLite is recommended behind the scenes
- Slide sequence: associated video plays first, then the paired event slide
