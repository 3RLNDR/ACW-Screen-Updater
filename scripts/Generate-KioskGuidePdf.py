from pathlib import Path


PAGE_W = 595
PAGE_H = 842
MARGIN_X = 54
TOP_Y = 788
BOTTOM_Y = 62


CONTENT = [
    ("title", "ACW Raspberry Pi Kiosk Setup Guide"),
    ("meta", "Follow this guide to make the Pi boot straight into the fullscreen slideshow."),
    ("space", ""),
    ("h1", "1. Put the project on the Pi"),
    ("body", "Clone or copy the repository to a stable location. The examples below assume:"),
    ("code", "/opt/acw-screen-updater"),
    ("body", "Then install the Python dependencies:"),
    ("code", "cd /opt/acw-screen-updater"),
    ("code", "python3 -m pip install -r requirements.txt"),
    ("space", ""),
    ("h1", "2. Test the app manually"),
    ("body", "Run a refresh once, then start the local web app:"),
    ("code", "python3 -m pi_display.refresh"),
    ("code", "python3 -m pi_display.web"),
    ("body", "Open these URLs on the Pi to confirm the dashboard and display are working:"),
    ("bullet", "http://localhost:8080/"),
    ("bullet", "http://localhost:8080/fullscreen.html?includeClasses=false"),
    ("body", "Use the dashboard to upload a promo video and link it to an event. The fullscreen screen should then show the video first and the booking slide second."),
    ("space", ""),
    ("h1", "3. Install the systemd services"),
    ("body", "Copy these files from the repository into /etc/systemd/system/:"),
    ("bullet", "systemd/acw-display.service"),
    ("bullet", "systemd/acw-refresh.service"),
    ("bullet", "systemd/acw-refresh.timer"),
    ("body", "Then enable them:"),
    ("code", "sudo systemctl daemon-reload"),
    ("code", "sudo systemctl enable --now acw-display.service"),
    ("code", "sudo systemctl enable --now acw-refresh.timer"),
    ("body", "Check service status:"),
    ("code", "sudo systemctl status acw-display.service"),
    ("code", "sudo systemctl status acw-refresh.timer"),
    ("space", ""),
    ("h1", "4. Create the kiosk launcher script"),
    ("body", "Create this file on the Pi:"),
    ("code", "/opt/acw-screen-updater/scripts/start-kiosk.sh"),
    (
        "codeblock",
        "#!/bin/bash\n"
        "set -e\n\n"
        "export DISPLAY=:0\n"
        "export XAUTHORITY=/home/pi/.Xauthority\n\n"
        "xset s off\n"
        "xset -dpms\n"
        "xset s noblank\n\n"
        "chromium-browser \\\n"
        "  --kiosk \\\n"
        "  --incognito \\\n"
        "  --disable-infobars \\\n"
        "  --noerrdialogs \\\n"
        "  --check-for-update-interval=31536000 \\\n"
        "  --overscroll-history-navigation=0 \\\n"
        "  http://localhost:8080/fullscreen.html?includeClasses=false",
    ),
    ("body", "Make it executable:"),
    ("code", "chmod +x /opt/acw-screen-updater/scripts/start-kiosk.sh"),
    ("space", ""),
    ("h1", "5. Create the autostart desktop entry"),
    ("body", "If needed, create the autostart folder first:"),
    ("code", "mkdir -p /home/pi/.config/autostart"),
    ("body", "Then create this file:"),
    ("code", "/home/pi/.config/autostart/acw-display.desktop"),
    (
        "codeblock",
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=ACW Display\n"
        "Exec=/opt/acw-screen-updater/scripts/start-kiosk.sh\n"
        "X-GNOME-Autostart-enabled=true",
    ),
    ("space", ""),
    ("h1", "6. Adjust values if needed"),
    ("bullet", "If your Pi username is not pi, change /home/pi/.Xauthority and the autostart path to match your real home folder."),
    ("bullet", "If Chromium is installed as chromium instead of chromium-browser, swap that command in the launcher script."),
    ("bullet", "If you want classes included in the display, change the URL to http://localhost:8080/fullscreen.html?includeClasses=true."),
    ("space", ""),
    ("h1", "7. Reboot and verify"),
    ("body", "After reboot, the Pi should:"),
    ("bullet", "start the ACW web app"),
    ("bullet", "run scheduled refreshes in the background"),
    ("bullet", "open Chromium in kiosk mode"),
    ("bullet", "display the fullscreen slideshow automatically"),
    ("body", "From another device on the same network, you can open the dashboard at http://<pi-ip>:8080/ to upload videos and change event associations."),
    ("space", ""),
    ("h1", "8. Useful maintenance commands"),
    ("code", "sudo systemctl restart acw-display.service"),
    ("code", "sudo systemctl start acw-refresh.service"),
    ("code", "journalctl -u acw-display.service -n 100 --no-pager"),
    ("code", "journalctl -u acw-refresh.service -n 100 --no-pager"),
    ("space", ""),
    ("h1", "Quick checklist"),
    ("bullet", "Project copied to /opt/acw-screen-updater"),
    ("bullet", "Dependencies installed"),
    ("bullet", "Refresh and web app tested manually"),
    ("bullet", "systemd units enabled"),
    ("bullet", "start-kiosk.sh created and made executable"),
    ("bullet", "acw-display.desktop created"),
    ("bullet", "Pi reboots into the fullscreen display"),
]


FONT_METRICS = {
    "Helvetica": 0.53,
    "Helvetica-Bold": 0.56,
    "Courier": 0.60,
}


STYLES = {
    "title": ("Helvetica-Bold", 22, 28, 0),
    "meta": ("Helvetica", 11, 16, 0),
    "h1": ("Helvetica-Bold", 15, 21, 0),
    "body": ("Helvetica", 11, 16, 0),
    "bullet": ("Helvetica", 11, 16, 16),
    "code": ("Courier", 10, 14, 18),
}


def wrap_text(text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    factor = FONT_METRICS[font] * size
    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) * factor <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_lines() -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []
    for kind, text in CONTENT:
        if kind == "space":
            lines.append({"text": "", "font": "Helvetica", "size": 8, "leading": 10, "indent": 0})
            continue

        if kind == "codeblock":
            for raw in text.split("\n"):
                lines.append({"text": raw, "font": "Courier", "size": 9.5, "leading": 13, "indent": 22})
            lines.append({"text": "", "font": "Helvetica", "size": 8, "leading": 9, "indent": 0})
            continue

        font, size, leading, indent = STYLES[kind]
        max_width = PAGE_W - MARGIN_X * 2 - indent
        wrapped = wrap_text(text, font, size, max_width)

        if kind == "bullet":
            for index, part in enumerate(wrapped):
                prefix = "- " if index == 0 else "  "
                lines.append({"text": f"{prefix}{part}", "font": font, "size": size, "leading": leading, "indent": indent})
            continue

        for part in wrapped:
            lines.append({"text": part, "font": font, "size": size, "leading": leading, "indent": indent})

    return lines


def paginate(lines: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    pages: list[list[dict[str, object]]] = []
    current_page: list[dict[str, object]] = []
    y = TOP_Y

    for line in lines:
        leading = float(line["leading"])
        if y - leading < BOTTOM_Y:
            pages.append(current_page)
            current_page = []
            y = TOP_Y

        entry = dict(line)
        entry["y"] = y
        current_page.append(entry)
        y -= leading

    if current_page:
        pages.append(current_page)

    return pages


def build_pdf_bytes() -> bytes:
    font_names = {"Helvetica": "F1", "Helvetica-Bold": "F2", "Courier": "F3"}
    font_objects = {
        "F1": b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "F2": b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        "F3": b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }

    objects: list[bytes | None] = []
    for name in ("F1", "F2", "F3"):
        objects.append(font_objects[name])

    lines = build_lines()
    pages = paginate(lines)

    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []
    next_object_number = 4

    for page_index, page_lines in enumerate(pages, start=1):
        commands = ["BT"]
        current_font = None
        current_size = None

        for item in page_lines:
            font_key = font_names[str(item["font"])]
            size = float(item["size"])
            if (font_key, size) != (current_font, current_size):
                commands.append(f"/{font_key} {size:.2f} Tf")
                current_font = font_key
                current_size = size

            x = MARGIN_X + float(item["indent"])
            y = float(item["y"])
            commands.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm")
            commands.append(f"({pdf_escape(str(item['text']))}) Tj")

        commands.append("/F1 9 Tf")
        commands.append(f"1 0 0 1 {PAGE_W - MARGIN_X - 70:.2f} 28.00 Tm")
        commands.append(f"(Page {page_index} of {len(pages)}) Tj")
        commands.append("ET")

        stream = "\n".join(commands).encode("latin-1", "replace")
        content_object = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        objects.append(content_object)
        content_object_numbers.append(next_object_number)
        next_object_number += 1

        page_object_numbers.append(next_object_number)
        objects.append(None)
        next_object_number += 1

    pages_object_number = next_object_number
    objects.append(None)
    next_object_number += 1

    catalog_object_number = next_object_number
    objects.append(None)

    for index, page_object_number in enumerate(page_object_numbers):
        content_object_number = content_object_numbers[index]
        objects[page_object_number - 1] = (
            f"<< /Type /Page /Parent {pages_object_number} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 1 0 R /F2 2 0 R /F3 3 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode("ascii")

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[pages_object_number - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("ascii")
    objects[catalog_object_number - 1] = f"<< /Type /Catalog /Pages {pages_object_number} 0 R >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]

    for object_number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(obj or b"")
        pdf.extend(b"\nendobj\n")

    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_object_number} 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    output_pdf = root / "output" / "pdf" / "acw-pi-kiosk-setup-guide.pdf"
    public_pdf = root / "public" / "guides" / "acw-pi-kiosk-setup-guide.pdf"

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    public_pdf.parent.mkdir(parents=True, exist_ok=True)

    pdf_bytes = build_pdf_bytes()
    output_pdf.write_bytes(pdf_bytes)
    public_pdf.write_bytes(pdf_bytes)

    print(output_pdf)
    print(public_pdf)
    print(output_pdf.stat().st_size)


if __name__ == "__main__":
    main()
