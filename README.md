# ACW Screen Updater

This repository now contains two versions of the Arts Centre Washington display site:

- the main version is a GitHub Pages-friendly static site
- the original local PowerShell server version is preserved in `backup-local-server/`

## Versions

### Main version: GitHub Pages

The root project is now designed for static hosting.

It works by:

- generating `public/events.json`
- downloading event images into `public/cache/images/`
- deploying the `public/` folder to GitHub Pages

The data refresh happens in GitHub Actions rather than in a long-running local server.

### Backup version: local PowerShell server

The original setup is preserved in:

- `backup-local-server/`

That version still uses:

- `Start-AcwDisplay.ps1`
- `/api/events`
- local image caching
- a Windows PC running the PowerShell server continuously

## GitHub Pages hosting

Yes, this project can now be hosted on GitHub Pages.

The deployment flow is:

1. GitHub Actions runs `scripts/Generate-StaticEvents.ps1`
2. The script scrapes Sunderland Culture
3. It writes fresh event data to `public/events.json`
4. It downloads event artwork into `public/cache/images/`
5. GitHub Pages publishes the `public/` folder

The included workflow is:

- `.github/workflows/deploy-pages.yml`

It runs:

- on pushes to `main`
- manually with `workflow_dispatch`
- once per day at 06:00 UTC on a schedule

## Important limitation

GitHub Pages is static hosting, so it does not run the PowerShell server.

That means:

- there is no live `/api/events` endpoint on GitHub Pages
- the site updates only when the GitHub Action runs and redeploys
- the current schedule is once per day at 06:00 UTC

You can still trigger a manual refresh at any time by running the workflow in GitHub Actions.

## Frontend files

- `public/index.html` dashboard view
- `public/fullscreen.html` fullscreen slideshow
- `public/app.js` dashboard logic
- `public/fullscreen.js` fullscreen slideshow logic
- `public/styles.css` styling and themes
- `public/events.json` generated event data

## Data generation

The GitHub Pages version uses:

- `scripts/Generate-StaticEvents.ps1`

That script:

- scrapes the Arts Centre Washington "What's On" page
- follows event pages for better dates, start times, and prices
- picks the largest available event image from listing markup
- downloads images into `public/cache/images/`
- writes a static JSON payload for the frontend

## Deploying to GitHub Pages

1. Push this repository to GitHub.
2. In GitHub, open `Settings > Pages`.
3. Set the source to `GitHub Actions`.
4. Push to `main` or run the workflow manually.

After that, GitHub will publish the site for you.

## Local use

### GitHub Pages version

To preview the static version locally, serve the `public/` folder through any local web server rather than opening the HTML files directly from disk.

### Original local-server version

If you want the old setup with the built-in scraper server, use the copy in:

- `backup-local-server/`

## Display modes

- Dashboard view: `index.html`
- Fullscreen slideshow: `fullscreen.html`
- Hide classes/courses: add `?includeClasses=false`
- Include classes in fullscreen: add `?includeClasses=true`
- Change slideshow delay: for example `?delay=15000`

Fullscreen defaults to:

- hiding classes and courses
- rotating one event at a time
- a 15 second delay between events

## Notes

- The scraper uses the public Arts Centre Washington "What's On" page at Sunderland Culture.
- If Sunderland Culture changes the page structure, `scripts/Generate-StaticEvents.ps1` may need updating.
- The backup PowerShell version is intentionally kept separate so you can return to the old local-server workflow if needed.
