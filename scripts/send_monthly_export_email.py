from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    manifest_path = Path("output/monthly-export/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    download_url = required_env("EXPORT_DOWNLOAD_URL")

    message = EmailMessage()
    message["Subject"] = f"ACW monthly slide export: {manifest['windowLabel']}"
    message["From"] = required_env("EXPORT_EMAIL_FROM")
    message["To"] = required_env("EXPORT_EMAIL_TO")

    lines = [
        f"Monthly slide export ready for {manifest['windowLabel']}.",
        f"Slides generated: {manifest['generatedCount']}.",
        f"Download: {download_url}",
    ]
    warnings = manifest.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {warning.get('title', 'Unknown event')}: {warning.get('reason', 'unspecified warning')}")

    message.set_content("\n".join(lines))

    smtp_host = required_env("EXPORT_SMTP_HOST")
    smtp_port = int(required_env("EXPORT_SMTP_PORT"))
    smtp_username = required_env("EXPORT_SMTP_USERNAME")
    smtp_password = required_env("EXPORT_SMTP_PASSWORD")

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


if __name__ == "__main__":
    main()
