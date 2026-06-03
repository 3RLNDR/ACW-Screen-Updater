from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from email.generator import _make_boundary
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

from pi_display.config import AppConfig
from pi_display.database import DisplayDatabase
from pi_display.publisher import build_output_payloads

Handler = Callable[[dict[str, Any], re.Match[str] | None], "HttpResponse"]


@dataclass
class HttpResponse:
    status_code: int
    body: bytes
    content_type: str = "text/plain; charset=utf-8"
    headers: list[tuple[str, str]] | None = None

    def to_wsgi(self, start_response: Callable[..., Any]) -> list[bytes]:
        reason = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }.get(self.status_code, "OK")
        headers = [
            ("Content-Type", self.content_type),
            ("Content-Length", str(len(self.body))),
        ]
        headers.extend(self.headers or [])
        start_response(f"{self.status_code} {reason}", headers)
        return [self.body]

    @classmethod
    def json(cls, payload: Any, status_code: int = 200) -> "HttpResponse":
        return cls(
            status_code=status_code,
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    @classmethod
    def text(
        cls,
        text: str,
        status_code: int = 200,
        content_type: str = "text/plain; charset=utf-8",
    ) -> "HttpResponse":
        return cls(
            status_code=status_code,
            body=text.encode("utf-8"),
            content_type=content_type,
        )


class TestResponse:
    def __init__(self, status_code: int, data: bytes, headers: dict[str, str]):
        self.status_code = status_code
        self.data = data
        self.headers = headers

    def json(self) -> Any:
        return json.loads(self.data.decode("utf-8"))

    @property
    def text(self) -> str:
        return self.data.decode("utf-8")


class TestClient:
    def __init__(self, app: "MiniApp"):
        self.app = app

    def get(self, path: str) -> TestResponse:
        return self.request("GET", path)

    def delete(self, path: str) -> TestResponse:
        return self.request("DELETE", path)

    def put(self, path: str, json: dict[str, Any] | None = None) -> TestResponse:
        payload = b""
        headers: dict[str, str] = {}
        if json is not None:
            payload = __import__("json").dumps(json).encode("utf-8")
            headers["CONTENT_TYPE"] = "application/json"
        return self.request("PUT", path, body=payload, extra_environ=headers)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        files: dict[str, tuple[str, BytesIO, str]] | None = None,
    ) -> TestResponse:
        headers: dict[str, str] = {}
        payload = b""
        if json is not None:
            payload = __import__("json").dumps(json).encode("utf-8")
            headers["CONTENT_TYPE"] = "application/json"
        elif files:
            boundary = _make_boundary()
            chunks: list[bytes] = []
            for field_name, (filename, fileobj, content_type) in files.items():
                chunks.extend(
                    [
                        f"--{boundary}\r\n".encode("utf-8"),
                        (
                            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                        ).encode("utf-8"),
                        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                        fileobj.read(),
                        b"\r\n",
                    ]
                )
            chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
            payload = b"".join(chunks)
            headers["CONTENT_TYPE"] = f"multipart/form-data; boundary={boundary}"
        return self.request("POST", path, body=payload, extra_environ=headers)

    def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        extra_environ: dict[str, str] | None = None,
    ) -> TestResponse:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        parsed_path = path.split("?", 1)
        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = parsed_path[0]
        environ["QUERY_STRING"] = parsed_path[1] if len(parsed_path) > 1 else ""
        environ["wsgi.input"] = BytesIO(body)
        environ["CONTENT_LENGTH"] = str(len(body))
        for key, value in (extra_environ or {}).items():
            environ[key] = value

        status: dict[str, Any] = {}

        def start_response(status_line: str, headers: list[tuple[str, str]]) -> None:
            status["status_code"] = int(status_line.split(" ", 1)[0])
            status["headers"] = dict(headers)

        chunks = self.app(environ, start_response)
        return TestResponse(status["status_code"], b"".join(chunks), status["headers"])


class MiniApp:
    def __init__(self, config: AppConfig, database: DisplayDatabase):
        self.config = config
        self.database = database
        self.routes: list[tuple[str, re.Pattern[str], Handler]] = []

    def route(self, method: str, pattern: str) -> Callable[[Handler], Handler]:
        regex = re.compile(pattern)

        def decorator(handler: Handler) -> Handler:
            self.routes.append((method.upper(), regex, handler))
            return handler

        return decorator

    def test_client(self) -> TestClient:
        return TestClient(self)

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        try:
            request = self._build_request(environ)
            for candidate_method, regex, handler in self.routes:
                if candidate_method != method:
                    continue
                match = regex.fullmatch(path)
                if match:
                    return handler(request, match).to_wsgi(start_response)

            if method == "GET":
                return self._serve_static(path).to_wsgi(start_response)

            return HttpResponse.json({"error": "Not found"}, status_code=404).to_wsgi(
                start_response
            )
        except Exception as error:  # pragma: no cover - emergency guard
            return HttpResponse.json({"error": str(error)}, status_code=500).to_wsgi(
                start_response
            )

    def _build_request(self, environ: dict[str, Any]) -> dict[str, Any]:
        body_length = int(environ.get("CONTENT_LENGTH") or 0)
        raw_body = environ["wsgi.input"].read(body_length) if body_length else b""
        content_type = environ.get("CONTENT_TYPE", "")
        request: dict[str, Any] = {
            "method": environ.get("REQUEST_METHOD", "GET").upper(),
            "path": environ.get("PATH_INFO", "/"),
            "query": {
                key: values[-1]
                for key, values in parse_qs(environ.get("QUERY_STRING", "")).items()
            },
            "body": raw_body,
            "json": None,
            "files": {},
        }

        environ["wsgi.input"] = BytesIO(raw_body)
        if content_type.startswith("application/json") and raw_body:
            request["json"] = json.loads(raw_body.decode("utf-8"))
        elif content_type.startswith("multipart/form-data"):
            request["files"] = parse_multipart_files(raw_body, content_type)
        return request

    def _serve_static(self, path: str) -> HttpResponse:
        if path == "/":
            target = self.config.public_dir / "index.html"
        else:
            target = (self.config.public_dir / path.lstrip("/")).resolve()
            if (
                self.config.public_dir.resolve() not in target.parents
                and target != self.config.public_dir.resolve()
            ):
                return HttpResponse.json({"error": "Not found"}, status_code=404)

        if not target.exists() or not target.is_file():
            return HttpResponse.json({"error": "Not found"}, status_code=404)

        mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return HttpResponse(
            status_code=200, body=target.read_bytes(), content_type=mime_type
        )


def get_header_parameter(value: str, parameter_name: str) -> str | None:
    match = re.search(rf'{parameter_name}=(?:"([^"]*)"|([^;]+))', value)
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").strip()


def parse_multipart_files(
    raw_body: bytes, content_type: str
) -> dict[str, dict[str, Any]]:
    boundary = get_header_parameter(content_type, "boundary")
    if not boundary:
        return {}

    files: dict[str, dict[str, Any]] = {}
    boundary_bytes = f"--{boundary}".encode("utf-8")
    for part in raw_body.split(boundary_bytes):
        if not part or part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        if b"\r\n\r\n" not in part:
            continue

        header_bytes, data = part.split(b"\r\n\r\n", 1)
        header_lines = header_bytes.decode("utf-8", errors="replace").split("\r\n")
        headers: dict[str, str] = {}
        for line in header_lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        disposition = headers.get("content-disposition", "")
        field_name = get_header_parameter(disposition, "name")
        filename = get_header_parameter(disposition, "filename")
        if not field_name or filename is None:
            continue

        if data.endswith(b"\r\n"):
            data = data[:-2]
        files[field_name] = {
            "filename": filename,
            "content_type": headers.get("content-type", "application/octet-stream"),
            "data": data,
        }

    return files


def load_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def republish_slides_from_current_events(
    config: AppConfig, database: DisplayDatabase
) -> dict[str, Any]:
    events_payload = load_json_file(
        config.public_dir / "events.json", {"items": [], "includeClasses": True}
    )
    _events_payload, slides_payload = build_output_payloads(
        events_payload.get("items", []),
        videos=database.get_video_map(),
        associations=database.list_event_video_map(),
        include_classes=bool(events_payload.get("includeClasses", True)),
    )
    (config.public_dir / "slides.json").write_text(
        json.dumps(slides_payload, indent=2), encoding="utf-8"
    )
    return slides_payload


def create_app(root_dir: Path | str) -> MiniApp:
    config = AppConfig.from_root(Path(root_dir))
    for directory in (
        config.public_dir,
        config.video_dir,
        config.image_dir,
        config.qr_dir,
        config.data_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    database = DisplayDatabase(config.database_path)
    database.initialize()
    app = MiniApp(config, database)

    @app.route("GET", r"/api/events")
    def api_events(
        request: dict[str, Any], _match: re.Match[str] | None
    ) -> HttpResponse:
        payload = load_json_file(
            config.public_dir / "events.json", {"items": [], "includeClasses": False}
        )
        include_classes = request["query"].get("includeClasses")
        if include_classes == "false":
            payload["items"] = [
                item for item in payload.get("items", []) if not item.get("isClass")
            ]
            payload["total"] = len(payload["items"])
            payload["includeClasses"] = False
        return HttpResponse.json(payload)

    @app.route("GET", r"/api/slides")
    def api_slides(
        _request: dict[str, Any], _match: re.Match[str] | None
    ) -> HttpResponse:
        payload = load_json_file(
            config.public_dir / "slides.json", {"slides": [], "total": 0}
        )
        return HttpResponse.json(payload)

    @app.route("GET", r"/api/videos")
    def api_videos(
        _request: dict[str, Any], _match: re.Match[str] | None
    ) -> HttpResponse:
        return HttpResponse.json({"items": database.list_videos()})

    @app.route("GET", r"/api/video-associations")
    def api_video_associations(
        _request: dict[str, Any], _match: re.Match[str] | None
    ) -> HttpResponse:
        return HttpResponse.json({"items": database.list_event_video_map()})

    @app.route("POST", r"/api/videos")
    def api_upload_video(
        request: dict[str, Any], _match: re.Match[str] | None
    ) -> HttpResponse:
        file_info = request["files"].get("file")
        if not file_info:
            return HttpResponse.json({"error": "file is required"}, status_code=400)

        filename = Path(file_info["filename"]).name
        file_hash = hashlib.sha1(file_info["data"]).hexdigest()[:8]
        stored_name = (
            f"{Path(filename).stem}-{file_hash}{Path(filename).suffix.lower()}"
        )
        destination = config.video_dir / stored_name
        destination.write_bytes(file_info["data"])
        video_id = f"video-{file_hash}"
        storage_path = f"./cache/videos/{stored_name}"

        database.save_video(
            video_id=video_id,
            title=Path(filename).stem.replace("-", " ").replace("_", " ").title(),
            filename=stored_name,
            storage_path=storage_path,
            mime_type=file_info["content_type"],
            duration_seconds=None,
        )
        slides_payload = republish_slides_from_current_events(config, database)
        return HttpResponse.json(
            {
                "video": {
                    "id": video_id,
                    "src": storage_path,
                    "title": Path(filename).stem,
                },
                "slidesUpdated": True,
                "slideTotal": slides_payload["total"],
            },
            status_code=201,
        )

    @app.route("PUT", r"/api/video-associations/(?P<event_id>[^/]+)")
    def api_set_association(
        request: dict[str, Any], match: re.Match[str] | None
    ) -> HttpResponse:
        payload = request.get("json") or {}
        video_id = payload.get("videoId")
        if not video_id:
            return HttpResponse.json({"error": "videoId is required"}, status_code=400)
        event_id = match.group("event_id") if match else ""
        database.set_event_video(event_id=event_id, video_id=video_id)
        slides_payload = republish_slides_from_current_events(config, database)
        return HttpResponse.json(
            {
                "eventId": event_id,
                "videoId": video_id,
                "slidesUpdated": True,
                "slideTotal": slides_payload["total"],
            }
        )

    @app.route("DELETE", r"/api/video-associations/(?P<event_id>[^/]+)")
    def api_clear_association(
        _request: dict[str, Any], match: re.Match[str] | None
    ) -> HttpResponse:
        event_id = match.group("event_id") if match else ""
        database.clear_event_video(event_id)
        slides_payload = republish_slides_from_current_events(config, database)
        return HttpResponse.json(
            {
                "eventId": event_id,
                "cleared": True,
                "slidesUpdated": True,
                "slideTotal": slides_payload["total"],
            }
        )

    return app


def main() -> None:
    app = create_app(Path.cwd())
    with make_server("0.0.0.0", 8080, app) as server:
        print("Serving ACW display on http://0.0.0.0:8080")
        server.serve_forever()


if __name__ == "__main__":
    main()
