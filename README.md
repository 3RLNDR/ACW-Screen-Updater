# ACW Screen Updater

This project powers an Arts Centre Washington event display.

It runs as a static site from `public/`, suitable for GitHub Pages or any simple static web server.

The display pulls event information from the Sunderland Culture "What's On" page for Arts Centre Washington, normalises the event data, and shows it in two browser views:

- `public/index.html` for a dashboard-style control view
- `public/fullscreen.html` for a rotating full-screen venue display

## What is in this repository

The root project contains the static display and its data generator:

- `scripts/Generate-StaticEvents.ps1` builds a static `public/events.json` file and downloads event artwork into `public/cache/images/`
- `.github/workflows/deploy-pages.yml` publishes the `public/` folder to GitHub Pages

## How the app works

1. GitHub Actions runs `scripts/Generate-StaticEvents.ps1`
2. The script scrapes the Sunderland Culture Arts Centre Washington page
3. It follows event detail pages to improve dates, start times, and prices
4. It downloads event images into `public/cache/images/`
5. It writes the final payload to `public/events.json`
6. GitHub Pages serves the `public/` folder

In this mode the frontend reads from `events.json`.

## Views

### Dashboard

`public/index.html` shows:

- the current display mode
- last refresh time
- event count
- controls for including or excluding classes and courses
- links to the fullscreen display
- a fullscreen theme picker

The page refreshes data every 5 minutes and also supports manual refresh.

### Fullscreen display

`public/fullscreen.html` shows:

- one event at a time
- a rotating slideshow
- event image or generated fallback poster artwork
- category, title, date, time, and price
- theme-controlled fullscreen styling

The default slide delay is 15 seconds, with a minimum allowed delay of 5 seconds.

`public/test-output.html` is the static preview companion for layout checks and should be updated alongside visible UI changes to the display.

## URL options

The frontend supports a few useful query-string options:

- `?includeClasses=false` hides classes and courses
- `?includeClasses=true` includes classes and courses
- `?theme=heritage`
- `?theme=midnight`
- `?theme=evergreen`
- `?theme=spotlight`
- `?delay=15000` sets the fullscreen slide duration in milliseconds

Defaults:

- dashboard includes classes unless local storage says otherwise
- fullscreen includes classes unless `includeClasses=false` is supplied
- fullscreen theme defaults to `heritage`

## Data shape

The static generator produces this payload shape:

- `fetchedAt`
- `includeClasses`
- `sourceUrl`
- `total`
- `items`
- `lastError`

Each event item includes fields such as:

- `title`
- `category`
- `isClass`
- `dateText`
- `startTime`
- `cost`
- `status`
- `meta`
- `link`
- `image`
- `imageLocal`
- `qrLocal`

## Running locally

Run:

```powershell
.\scripts\Generate-StaticEvents.ps1
```

This writes:

- `public/events.json`
- `public/cache/images/*`

Then serve `public/` through any local web server.

Example:

```powershell
python -m http.server 8000 --directory public
```

Then open:

- `http://localhost:8000/`

Important: opening the HTML files directly with `file://` does not load real event data. In direct file mode the frontend falls back to built-in preview items.

## Deployment

GitHub Pages deployment is defined in [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml).

The workflow:

- runs on pushes to `main`
- supports manual runs through `workflow_dispatch`
- runs daily at `06:00 UTC`
- uses a Windows runner to build the static event payload
- uploads the `public/` folder as the Pages artifact

To use Pages:

1. Push the repository to GitHub.
2. In the repository settings, set Pages to use `GitHub Actions`.
3. Let the workflow publish the `public/` folder.

## Key files

- [README.md](README.md)
- [scripts/Generate-StaticEvents.ps1](scripts/Generate-StaticEvents.ps1)
- [public/index.html](public/index.html)
- [public/app.js](public/app.js)
- [public/fullscreen.html](public/fullscreen.html)
- [public/fullscreen.js](public/fullscreen.js)
- [public/styles.css](public/styles.css)
- [public/events.json](public/events.json)

## Notes and limitations

- The scraper depends on the current HTML structure of the Sunderland Culture site. If that markup changes, parsing may need to be updated.
- The display only updates when the static generation workflow runs, or when `scripts/Generate-StaticEvents.ps1` is run locally.
- Some older sample data in the frontend fallback arrays still contains mis-encoded pound signs (`Â£`), but the live/static data pipeline includes logic to normalise currency display.
