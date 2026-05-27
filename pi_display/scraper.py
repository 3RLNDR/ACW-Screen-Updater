from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests

SOURCE_URL = "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
CLASS_CATEGORIES = {
    "Adult Workshops and Activities",
    "Children and Young People's Activities",
}
ALLOWED_SECTIONS = {
    "Theatre and Performance",
    "Music",
    "Comedy",
    "Films",
    "Talks",
    "Adult Workshops and Activities",
    "Children and Young People's Activities",
    "Exhibitions",
    "Special Events",
}
MONTH_PATTERN = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DETAIL_CACHE: dict[str, dict[str, Any] | None] = {}


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u2013", "-")
        .replace("Ã‚Â£", "\u00A3")
    )
    return re.sub(r"\s+", " ", text).strip()


def normalize_compare_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_whitespace(value).lower())


def normalize_currency_text(value: str | None) -> str | None:
    text = normalize_whitespace(value)
    if not text:
      return None
    text = re.sub(r"^(Tickets?\s*)", "", text, flags=re.IGNORECASE)
    if re.search(r"\bfree\b", text, flags=re.IGNORECASE):
      return "Free"
    match = re.search(r"\u00A3\s*\d+(?:\.\d{2})?", text)
    if match:
      amount = re.sub(r"^\u00A3\s*", "", match.group(0))
      return f"\u00A3{amount}"
    return text


def convert_to_plain_text(html: str | None) -> str:
    if not html:
        return ""
    text = re.sub(r"(?is)<script.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6)>", "\n", text)
    text = re.sub(r"(?is)<.*?>", " ", text)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"[\r\t]", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_absolute_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    return urljoin(SOURCE_URL, url)


def get_date_text_from_lines(lines: list[str]) -> str | None:
    current_year = datetime.now().year
    patterns = [
        rf"\b\d{{1,2}}\s*-\s*\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\b",
        rf"\b\d{{1,2}}\s+{MONTH_PATTERN}\s*-\s*\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\b",
        rf"\b\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\b",
        rf"\b\d{{1,2}}\s*-\s*\d{{1,2}}\s+{MONTH_PATTERN}\b",
        rf"\b\d{{1,2}}\s+{MONTH_PATTERN}\s*-\s*\d{{1,2}}\s+{MONTH_PATTERN}\b",
        rf"\b\d{{1,2}}\s+{MONTH_PATTERN}\b",
    ]
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if not match:
                continue
            value = normalize_whitespace(match.group(0))
            if not re.search(r"\b\d{4}\b", value):
                value = f"{value} {current_year}"
            return value
    return None


def get_start_time_from_lines(lines: list[str]) -> str | None:
    for line in lines:
        match = re.search(r"\b\d{1,2}(?::|\.)?\d{0,2}\s*(am|pm)\b", line, flags=re.IGNORECASE)
        if match:
            return normalize_whitespace(match.group(0).lower()).replace(".", ":")
    return None


def get_cost_from_lines(lines: list[str], badges: list[str]) -> str | None:
    if "Free" in badges:
        return "Free"
    for line in lines:
        match = re.search(r"(Tickets?\s*)?(\u00A3\s*\d+(?:\.\d{2})?|Free)", normalize_whitespace(line), flags=re.IGNORECASE)
        if match:
            return normalize_currency_text(match.group(0))
    return None


def get_date_sort_key(date_text: str | None) -> datetime:
    if not date_text:
        return datetime.max

    match = re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}", date_text)
    if not match:
        fallback = re.search(r"^(\d{1,2})\s*-\s*\d{1,2}\s+([A-Za-z]{3,9})\s+(\d{4})", date_text)
        if fallback:
            match_value = f"{fallback.group(1)} {fallback.group(2)} {fallback.group(3)}"
        else:
            return datetime.max
    else:
        match_value = match.group(0)

    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(match_value, fmt)
        except ValueError:
            continue
    return datetime.max


def get_sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def invoke_node_fetch(url: str, out_file: Path | None = None) -> bytes | str:
    fetch_helper = Path(__file__).resolve().parent.parent / "scripts" / "fetch-url.mjs"
    arguments = ["node", str(fetch_helper), url]
    if out_file is not None:
        arguments.extend(["--out", str(out_file)])
    completed = subprocess.run(arguments, check=True, capture_output=out_file is None)
    if out_file is not None:
        return b""
    return completed.stdout.decode("utf-8")


def get_web_content(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9",
        "Referer": SOURCE_URL,
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception:
        return str(invoke_node_fetch(url))


def download_web_file(url: str, destination: Path) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        "Referer": SOURCE_URL,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        destination.write_bytes(response.content)
    except Exception:
        invoke_node_fetch(url, destination)


def save_image(config: Any, url: str | None) -> str | None:
    if not url:
        return None
    ext = Path(urlparse(url).path).suffix or ".img"
    filename = f"{get_sha1_hex(url)}{ext.lower()}"
    destination = config.image_dir / filename
    if not destination.exists():
        download_web_file(url, destination)
    return f"cache/images/{filename}"


def save_qr_code(config: Any, url: str | None) -> str | None:
    if not url:
        return None
    filename = f"{get_sha1_hex(url)}.png"
    destination = config.qr_dir / filename
    if destination.exists():
        return f"cache/qr/{filename}"

    providers = [
        f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=0&data={quote_plus(url)}",
        f"https://quickchart.io/qr?size=220&margin=0&text={quote_plus(url)}",
    ]

    for provider_url in providers:
        try:
            download_web_file(provider_url, destination)
            if destination.exists():
                return f"cache/qr/{filename}"
        except Exception:
            if destination.exists():
                destination.unlink(missing_ok=True)
    return None


def get_best_image_url(html: str) -> str | None:
    patterns = [
        r'(?is)\sdata-srcset="([^"]+)"',
        r'(?is)\ssrcset="([^"]+)"',
        r'(?is)\sdata-src="([^"]+)"',
        r'(?is)\ssrc="([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if not match:
            continue
        value = match.group(1).strip()
        if "srcset" in pattern:
            candidates = []
            for entry in value.split(","):
                parts = entry.strip().split()
                if not parts:
                    continue
                width_match = re.match(r"^(\d+)w$", parts[1]) if len(parts) > 1 else None
                candidates.append((parts[0], int(width_match.group(1)) if width_match else 0))
            if candidates:
                best = sorted(candidates, key=lambda item: item[1], reverse=True)[0][0]
                return get_absolute_url(best)
        else:
            return get_absolute_url(value)
    return None


def get_card_link(html: str) -> str | None:
    permalink = re.search(r'(?is)<a[^>]+class="[^"]*\bc-event-card__permalink\b[^"]*"[^>]+href="([^"]+)"', html)
    if permalink:
        return get_absolute_url(permalink.group(1))

    urls = []
    for match in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>', html):
        url = get_absolute_url(match.group(1))
        if url:
            urls.append(url)
    for url in urls:
        if "?type=" not in url and "/whats-on/" in url:
            return url
    return urls[0] if urls else None


def get_card_blocks(section_html: str) -> list[str]:
    container_matches = list(
        re.finditer(r'(?is)<div[^>]+class="[^"]*\bc-col-events-block__event-card-container\b[^"]*"[^>]*>', section_html)
    )
    if container_matches:
        blocks = []
        for index, match in enumerate(container_matches):
            start = match.start()
            end = container_matches[index + 1].start() if index + 1 < len(container_matches) else len(section_html)
            blocks.append(section_html[start:end])
        return blocks
    return [match.group(0) for match in re.finditer(r'(?is)<a\b[^>]*>.*?<h3[^>]*>.*?</h3>.*?</a>', section_html)]


def get_event_details(url: str) -> dict[str, Any] | None:
    if not url:
        return None
    if url in DETAIL_CACHE:
        return DETAIL_CACHE[url]

    try:
        content = get_web_content(url)
        lines = split_lines(convert_to_plain_text(content))
        date_text = None
        start_time = None
        cost = None
        summary_pattern = re.compile(
            r"(?P<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]{3,9})(?:,\s*(?P<time>\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm)))?(?:,\s*Tickets?\s*(?P<price>[^,]+))?",
            flags=re.IGNORECASE,
        )

        for line in lines:
            summary = summary_pattern.search(line)
            if summary:
                if not date_text:
                    parsed = datetime.strptime(f"{summary.group('date')} {datetime.now().year}", "%A %d %B %Y")
                    date_text = parsed.strftime("%d %b %Y")
                if not start_time and summary.group("time"):
                    start_time = normalize_whitespace(summary.group("time").lower()).replace(".", ":")
                if not cost and summary.group("price"):
                    cost = normalize_currency_text(summary.group("price"))
                break

        if not date_text:
            date_text = get_date_text_from_lines(lines)
        if not start_time:
            start_time = get_start_time_from_lines(lines)
        if not cost:
            cost = get_cost_from_lines(lines, [])

        start_date_match = re.search(r'"startDate"\s*:\s*"([^"]+)"', content)
        if start_date_match and (not date_text or not start_time):
            try:
                parsed = datetime.fromisoformat(start_date_match.group(1).replace("Z", "+00:00"))
                if not date_text:
                    date_text = parsed.strftime("%d %b %Y")
                if not start_time and re.search(r"T(?!00:00)(?!00:00:00)\d{2}:\d{2}", start_date_match.group(1)):
                    start_time = parsed.strftime("%I:%M%p").lower().lstrip("0").replace(":00", "")
            except ValueError:
                pass

        price_match = re.search(r'"(?:price|lowPrice)"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?', content)
        if not cost and price_match:
            cost = "Free" if price_match.group(1) == "0" else f"\u00A3{price_match.group(1).rstrip('0').rstrip('.')}"

        DETAIL_CACHE[url] = {"dateText": date_text, "startTime": start_time, "cost": cost}
    except Exception:
        DETAIL_CACHE[url] = None

    return DETAIL_CACHE[url]


def parse_source_html(config: Any, source_content: str, include_classes: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    sections = list(re.finditer(r"(?is)<h2[^>]*>(.*?)</h2>", source_content))
    for index, section in enumerate(sections):
        section_title = normalize_whitespace(section.group(1)).replace("&", "and")
        if section_title not in ALLOWED_SECTIONS:
            continue
        if not include_classes and section_title in CLASS_CATEGORIES:
            continue

        start = section.end()
        end = sections[index + 1].start() if index + 1 < len(sections) else len(source_content)
        section_html = source_content[start:end]
        cards = get_card_blocks(section_html)
        for card in cards:
            title_match = re.search(r"(?is)<h3[^>]*>(.*?)</h3>", card)
            if not title_match:
                continue
            title = normalize_whitespace(title_match.group(1))
            if not title:
                continue

            event_link = get_card_link(card)
            image_url = get_best_image_url(card)
            lines = split_lines(convert_to_plain_text(card))
            badges = [badge for badge in ["Free", "Sold Out", "Limited Availability"] if badge in lines]
            listing_date_text = get_date_text_from_lines(lines)
            date_text = listing_date_text
            start_time = get_start_time_from_lines(lines)
            cost = get_cost_from_lines(lines, badges)

            if event_link:
                details = get_event_details(event_link)
                if details:
                    detail_fields_are_trusted = True
                    if not date_text and details.get("dateText"):
                        date_text = details["dateText"]
                    elif date_text and details.get("dateText"):
                        detail_fields_are_trusted = get_date_sort_key(date_text) == get_date_sort_key(details["dateText"])

                    if detail_fields_are_trusted:
                        start_time = details.get("startTime") or start_time
                        cost = details.get("cost") or cost

            title_key = normalize_compare_text(title)
            meta: list[str] = []
            for line in lines:
                if line in {section_title, title, "More", "Arts Centre Washington", date_text, start_time, cost}:
                    continue
                if line in badges:
                    continue
                line_key = normalize_compare_text(line)
                if re.match(r"^(View all|Part of|Book now|Book tickets|Register your interest)\b", line):
                    continue
                if line_key and (line_key == title_key or line_key in title_key or title_key in line_key):
                    continue
                meta.append(line)

            try:
                image_local = save_image(config, image_url)
            except Exception:
                image_local = None
            try:
                qr_local = save_qr_code(config, event_link)
            except Exception:
                qr_local = None

            results.append(
                {
                    "title": title,
                    "category": section_title,
                    "isClass": section_title in CLASS_CATEGORIES,
                    "dateText": date_text,
                    "startTime": start_time,
                    "cost": cost,
                    "sortDate": get_date_sort_key(date_text).isoformat() if date_text else "",
                    "status": " | ".join(badges),
                    "meta": meta[:3],
                    "link": event_link,
                    "image": image_url,
                    "imageLocal": image_local,
                    "qrLocal": qr_local,
                }
            )
    return results


def scrape_events(config: Any, include_classes: bool) -> list[dict[str, Any]]:
    config.image_dir.mkdir(parents=True, exist_ok=True)
    config.qr_dir.mkdir(parents=True, exist_ok=True)
    source_content = get_web_content(SOURCE_URL)
    results = parse_source_html(config, source_content, include_classes)
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in results:
      key = (item["title"], item["category"], item["dateText"] or "")
      current = deduped.get(key)
      if current is None or (item.get("imageLocal") and not current.get("imageLocal")):
          deduped[key] = item

    items = sorted(deduped.values(), key=lambda item: (get_date_sort_key(item.get("dateText")), item["title"]))
    if not items:
        fallback_path = config.public_dir / "events.json"
        if fallback_path.exists():
            payload = json.loads(fallback_path.read_text(encoding="utf-8"))
            items = [item for item in payload.get("items", []) if include_classes or not item.get("isClass")]
    return items


def scrape_events_from_fixture(source_path: Path) -> list[dict[str, Any]]:
    return json.loads(source_path.read_text(encoding="utf-8"))
