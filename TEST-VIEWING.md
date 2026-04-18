# Viewing The Test Page Locally

This project includes a fullscreen preview page at `public/test-output.html`.

Use it when you want to check the same fullscreen features as the live display without relying on live scraped data.

## Quickest option

Open this file directly in a browser:

- `C:\Users\chris\Documents\ACW Screen Updater\public\test-output.html`

When opened directly with `file://`, it runs in preview mode and uses the built-in sample events from the fullscreen script.

## Recommended option

Run a simple local web server from the project root:

```powershell
python -m http.server 8000 --directory public
```

Then open:

- `http://localhost:8000/test-output.html`

This is useful if you want the preview page to behave more like the hosted/static site.

## Live page vs test page

- `public/test-output.html` is the fullscreen test preview
- `public/index.html` is the dashboard/control page
- `public/fullscreen.html` is the rotating live display page

## Notes

- The test page now reuses the same fullscreen markup and script as the live display.
- When opened directly from disk, it uses sample fallback content.
- When served over HTTP, it can load `events.json` the same way as the live static site.
