# ACW Screen Updater

This project creates a screen-friendly event website for Arts Centre Washington that:

- scrapes the live "What's On" listings from Sunderland Culture
- downloads and caches event artwork locally when available
- can include or hide classes and courses
- provides both a dashboard view and a fullscreen slideshow view
- auto-refreshes so a tiny PC can stay connected to a venue TV

## How it works

The project has two parts:

- `public/` contains the website shown on the TV
- `Start-AcwDisplay.ps1` runs a small local web server that scrapes live events and serves them to the website at `/api/events`

That means the live site is not just static HTML. The frontend depends on the PowerShell server for:

- live event data
- cached images
- health checks

## Files

- `Start-AcwDisplay.ps1` starts the local web server and scraper
- `Run-Live-Display.bat` launches the server more easily on Windows
- `public/index.html` is the dashboard view
- `public/fullscreen.html` is the single-event fullscreen slideshow
- `public/app.js` handles live refresh, filtering, and dashboard rendering
- `public/fullscreen.js` handles the fullscreen rotation view
- `public/styles.css` contains layout, themes, and styling
- `public/test-output.html` is a standalone visual preview
- `cache/images` stores locally cached event artwork
- `server.log` records local server activity

## Run locally

Open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Start-AcwDisplay.ps1
```

Then open:

```text
http://localhost:8080/
```

If you prefer, you can also start it with:

```text
Run-Live-Display.bat
```

## Display modes

- Dashboard view: `http://localhost:8080/`
- Fullscreen slideshow: `http://localhost:8080/fullscreen.html`
- Hide classes/courses: add `?includeClasses=false`
- Include classes in fullscreen: add `?includeClasses=true`
- Change slideshow delay: for example `?delay=15000`

Fullscreen defaults to:

- hiding classes and courses
- rotating one event at a time
- a 15 second delay between events

## Useful endpoints

- `http://localhost:8080/` dashboard
- `http://localhost:8080/fullscreen.html` fullscreen slideshow
- `http://localhost:8080/api/events` all live events
- `http://localhost:8080/api/events?includeClasses=false` live events without classes
- `http://localhost:8080/health` basic server check

## Recommended TV setup

1. Put this folder on the tiny PC.
2. Create a shortcut that runs:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\chris\Documents\ACW Screen Updater\Start-AcwDisplay.ps1"
```

3. Add that shortcut to the Windows Startup folder.
4. Open the browser to:

```text
http://localhost:8080/fullscreen.html
```

5. Put the browser into fullscreen or kiosk mode.

## Can this be hosted on Netlify?

Not in its current form for the live version.

Why:

- Netlify is ideal for static sites and serverless functions
- this project currently relies on a long-running local PowerShell server
- the scraper logic lives in `Start-AcwDisplay.ps1`
- image caching is stored on the local filesystem in `cache/images`

So:

- `public/test-output.html` could be hosted on Netlify as a static preview
- the full live app cannot be deployed to Netlify unchanged

## What would be needed for Netlify hosting?

To host the live version on Netlify, we would need to convert the backend into a Netlify-friendly approach, for example:

1. Replace `Start-AcwDisplay.ps1` with a JavaScript or TypeScript Netlify Function.
2. Move the scraper into that function.
3. Return event JSON from a function endpoint instead of the local PowerShell API.
4. Change image handling so it does not depend on local disk caching, or store cached assets somewhere else.

That would let the frontend stay similar, but the backend would need to be rewritten.

## Best hosting options right now

For the current codebase, the best options are:

- a tiny Windows PC running the local PowerShell server
- a Windows mini PC connected directly to the TV
- a Windows server or always-on machine on the local network

If you want a cloud-hosted version, I can help convert this into:

- a Netlify Functions app
- a Node/Express app for a VPS
- or a static site plus scheduled data refresh pipeline

## Notes

- The scraper uses the public Arts Centre Washington "What's On" page at Sunderland Culture.
- Event images are fetched from the live site and then served locally from this app where possible.
- Classes and courses are mapped from:
  - `Adult Workshops and Activities`
  - `Children and Young People's Activities`
- If Sunderland Culture changes the page structure, the parser in `Start-AcwDisplay.ps1` may need a small update.

