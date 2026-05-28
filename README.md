# ACW Screen Updater

This project powers an Arts Centre Washington event display.

It supports three ways of running:

- a Raspberry Pi-hosted Python service for production hosting, scheduled refreshes, and video management
- a static site in `public/` for GitHub Pages
- a live local PowerShell server for a Windows display machine

The display pulls event information from the Sunderland Culture "What's On" page for Arts Centre Washington, normalises the event data, and shows it in two browser views:

- `public/index.html` for a dashboard-style control view
- `public/fullscreen.html` for a rotating full-screen venue display
- locally hosted promo videos that can be associated with event entries

## What is in this repository

The root project is now a hybrid working copy:

- `pi_display/` contains the Pi-native scraper, publisher, SQLite storage, and local web service
- `scripts/Generate-StaticEvents.ps1` builds a static `public/events.json` file and downloads event artwork into `public/cache/images/`
- `Start-AcwDisplay.ps1` runs a local HTTP server with a live `/api/events` endpoint and local image caching
- `systemd/` contains example service and timer units for Raspberry Pi deployment
- `.github/workflows/deploy-pages.yml` publishes the `public/` folder to GitHub Pages
- `backup-local-server/` keeps an older copy of the original local-server version as a fallback reference

So this is not just a GitHub Pages project and not just a local server project. The root contains both flows.

## How the app works

### Raspberry Pi production mode

This is now the preferred production path.

1. `python -m pi_display.refresh` scrapes the Sunderland Culture source and writes `public/events.json` plus `public/slides.json`
2. The Pi-hosted service serves the dashboard, fullscreen view, cached images, QR codes, and uploaded promo videos
3. Uploaded video metadata and event-to-video associations are stored in `data/acw-display.sqlite3`
4. The dashboard can upload local promo videos and link them to events
5. The fullscreen screen plays `video -> event` whenever an association exists

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
- a promo-video upload and event association panel when served by the Pi app

The page refreshes data every 5 minutes and also supports manual refresh.

### Fullscreen display

`public/fullscreen.html` shows:

- one slide at a time
- a rotating slideshow of event slides and optional video slides
- event image or generated fallback poster artwork
- locally hosted promo videos when configured
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

Both the static generator and the Pi publisher produce the same general event payload shape:

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

The Pi flow also generates `public/slides.json`, where each entry has a `type` of either `event` or `video`.

## Running locally

Important: the Raspberry Pi-hosted version is now the primary production deployment target. GitHub Pages remains useful as a static fallback preview, and the local PowerShell server is intended as a testing and validation environment for the display experience.

### Option 1: run the Raspberry Pi-style Python service

From the project root:

```powershell
python -m pi_display.refresh
python -m pi_display.web
```

Then open:

- `http://localhost:8080/`
- `http://localhost:8080/fullscreen.html?includeClasses=false`

This path enables:

- generated `events.json` and `slides.json`
- local video uploads under `public/cache/videos/`
- SQLite-backed event-to-video associations in `data/acw-display.sqlite3`
- the dashboard video-management UI

### Option 2: run the live local PowerShell server

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

Important: that batch file currently hardcodes `C:\Users\chris\Documents\ACW Screen Updater`. If the repo lives somewhere else, update the path before using it.

### Option 3: generate static data locally

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

### Raspberry Pi deployment

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

The example `systemd/` units can be copied into `/etc/systemd/system/`:

- `systemd/acw-display.service`
- `systemd/acw-refresh.service`
- `systemd/acw-refresh.timer`

Typical enable flow on the Pi:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now acw-display.service
sudo systemctl enable --now acw-refresh.timer
```

Operator workflow:

1. Open the dashboard on the Pi-hosted service.
2. Upload a promo video file.
3. Choose the matching event from the association list.
4. Open the fullscreen URL and confirm the video plays before the event slide.

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

### Monthly slide export email

The repository also includes a scheduled GitHub Actions workflow that prepares a monthly ZIP of upcoming event slides in:

- `16:9`
- `4:3`

The workflow:

- runs daily
- exits unless it is three days before month-end
- supports manual runs through `workflow_dispatch`
- uploads an export artifact
- emails a download link to the configured recipient

It runs on `windows-latest` because the current JPG renderer uses a Windows-native PowerShell image composition path.

Required secrets:

- `EXPORT_EMAIL_TO`
- `EXPORT_EMAIL_FROM`
- `EXPORT_SMTP_HOST`
- `EXPORT_SMTP_PORT`
- `EXPORT_SMTP_USERNAME`
- `EXPORT_SMTP_PASSWORD`

The email download link currently points to the GitHub Actions run page for the export run, where the uploaded artifact can be downloaded.

## Key files

- [README.md](/C:/Users/chris/Documents/ACW%20Screen%20Updater/README.md)
- [pi_display/](/C:/Users/chris/Documents/ACW%20Screen%20Updater/pi_display)
- [Start-AcwDisplay.ps1](/C:/Users/chris/Documents/ACW%20Screen%20Updater/Start-AcwDisplay.ps1)
- [Run-Live-Display.bat](/C:/Users/chris/Documents/ACW%20Screen%20Updater/Run-Live-Display.bat)
- [scripts/Generate-StaticEvents.ps1](/C:/Users/chris/Documents/ACW%20Screen%20Updater/scripts/Generate-StaticEvents.ps1)
- [public/index.html](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/index.html)
- [public/app.js](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/app.js)
- [public/fullscreen.html](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/fullscreen.html)
- [public/fullscreen.js](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/fullscreen.js)
- [public/styles.css](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/styles.css)
- [public/events.json](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/events.json)
- [public/slides.json](/C:/Users/chris/Documents/ACW%20Screen%20Updater/public/slides.json)
- [systemd/](/C:/Users/chris/Documents/ACW%20Screen%20Updater/systemd)
- [backup-local-server/](/C:/Users/chris/Documents/ACW%20Screen%20Updater/backup-local-server)

## Notes and limitations

- The scraper depends on the current HTML structure of the Sunderland Culture site. If that markup changes, parsing may need to be updated.
- The Python web service currently uses the standard-library `cgi` parser for uploads, which is deprecated in Python 3.13 and should be replaced during a future maintenance pass.
- The static GitHub Pages version is not live in the server sense. It only updates when the generation workflow runs.
- The live local server only supports `GET` requests.
- The live server exposes `GET /api/events` and `GET /health`.
- The live server stores its log in `server.log`.
- Some older sample data in the frontend fallback arrays still contains mis-encoded pound signs (`Â£`), but the live/static data pipeline includes logic to normalise currency display.
