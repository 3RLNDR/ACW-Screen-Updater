# ACW Screen Updater

This project powers an Arts Centre Washington event display.

It supports two ways of running:

- a static site in `public/` for GitHub Pages
- a live local PowerShell server for a Windows display machine

The display pulls event information from the Sunderland Culture "What's On" page for Arts Centre Washington, normalises the event data, and shows it in two browser views:

- `public/index.html` for a dashboard-style control view
- `public/fullscreen.html` for a rotating full-screen venue display

## What is in this repository

The root project is now a hybrid working copy:

- `scripts/Generate-StaticEvents.ps1` builds a static `public/events.json` file and downloads event artwork into `public/cache/images/`
- `Start-AcwDisplay.ps1` runs a local HTTP server with a live `/api/events` endpoint and local image caching
- `.github/workflows/deploy-pages.yml` publishes the `public/` folder to GitHub Pages
- `backup-local-server/` keeps an older copy of the original local-server version as a fallback reference

So this is not just a GitHub Pages project and not just a local server project. The root contains both flows.

## How the app works

### Static mode

This is the GitHub Pages-friendly path.

1. GitHub Actions runs `scripts/Generate-StaticEvents.ps1`
2. The script scrapes the Sunderland Culture Arts Centre Washington page
3. It follows event detail pages to improve dates, start times, and prices
4. It downloads event images into `public/cache/images/`
5. It writes the final payload to `public/events.json`
6. GitHub Pages serves the `public/` folder

In this mode the frontend reads from `events.json`.

### Live local mode

This is the Windows display-machine path.

1. `Start-AcwDisplay.ps1` starts a small local HTTP server on `http://localhost:8080`
2. The server scrapes Sunderland Culture on demand
3. Results are cached in memory for the configured refresh window
4. Remote images are cached locally under `cache/images/`
5. The frontend reads live data from `/api/events`

In this mode the local server also serves the files in `public/`.

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

`public/test-output.html` is the static preview companion for layout checks and should be updated alongside visible UI changes to the live display.

## URL options

The frontend supports a few useful query-string options:

- `?includeClasses=false` hides classes and courses
- `?includeClasses=true` includes classes and courses
- `?theme=heritage`
- `?theme=midnight`
- `?theme=evergreen`
- `?theme=spotlight`
- `?delay=15000` sets the fullscreen slide duration in milliseconds
- `?showImages=true` on the dashboard allows remote image URLs when available

Defaults:

- dashboard includes classes unless local storage says otherwise
- fullscreen excludes classes unless `includeClasses=true` is supplied
- fullscreen theme defaults to `heritage`

## Data shape

Both the static generator and the live server produce the same general payload shape:

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

### Option 1: run the live local server

From the project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-AcwDisplay.ps1
```

Optional parameters:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-AcwDisplay.ps1 -Port 8080 -RefreshMinutes 15
```

Then open:

- `http://localhost:8080/`
- `http://localhost:8080/fullscreen.html?includeClasses=false`

There is also a helper launcher:

- `Run-Live-Display.bat`

Important: that batch file currently hardcodes `C:\Users\chris\OneDrive\Documents\ACW Screen Updater`. If the repo lives somewhere else, update the path before using it.

### Option 2: generate static data locally

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

GitHub Pages deployment is defined in [deploy-pages.yml](/C:/Users/chris/Documents/ACW%20Screen%20Updater/.github/workflows/deploy-pages.yml).

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

- [README.md](/C:/Users/chris/Documents/ACW%20Screen%20Updater/README.md)
- [Start-AcwDisplay.ps1](/C:/Users/chris/Documents/ACW%20Screen%20Updater/Start-AcwDisplay.ps1)
- [Run-Live-Display.bat](/C:/Users/chris/Documents/ACW%20Screen%20Updater/Run-Live-Display.bat)
- [scripts/Generate-StaticEvents.ps1](/C:/Users/chris/Documents/ACW%20Screen%20Updater/scripts/Generate-StaticEvents.ps1)
- [public/index.html](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/index.html)
- [public/app.js](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/app.js)
- [public/fullscreen.html](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/fullscreen.html)
- [public/fullscreen.js](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/fullscreen.js)
- [public/styles.css](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/styles.css)
- [public/events.json](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/events.json)
- [backup-local-server/](/C:/Users/chris/Documents/ACW%20Screen%20Updater/backup-local-server)

## Notes and limitations

- The scraper depends on the current HTML structure of the Sunderland Culture site. If that markup changes, parsing may need to be updated.
- The static GitHub Pages version is not live in the server sense. It only updates when the generation workflow runs.
- The live local server only supports `GET` requests.
- The live server exposes `GET /api/events` and `GET /health`.
- The live server stores its log in `server.log`.
- Some older sample data in the frontend fallback arrays still contains mis-encoded pound signs (`Â£`), but the live/static data pipeline includes logic to normalise currency display.
