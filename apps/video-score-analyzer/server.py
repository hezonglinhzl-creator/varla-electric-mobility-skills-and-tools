from __future__ import annotations

import cgi
import json
import mimetypes
import shutil
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.analyzer import Paths, analyze_video


ROOT = Path(__file__).resolve().parent
PATHS = Paths(root=ROOT, uploads=ROOT / "uploads", reports=ROOT / "reports", exports=ROOT / "exports")
STATIC = ROOT / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "VideoScoreAnalyzer/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/":
            self.send_file(STATIC / "index.html")
            return
        if path.startswith("/static/"):
            self.send_file(STATIC / path.removeprefix("/static/"))
            return
        if path.startswith("/reports/"):
            self.send_file(PATHS.reports / path.removeprefix("/reports/"))
            return
        if path.startswith("/exports/"):
            self.send_file(PATHS.exports / path.removeprefix("/exports/"), download=True)
            return
        if path == "/api/health":
            self.send_json({"ok": True, "root": str(ROOT)})
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self.handle_analyze()
            return
        self.send_error(404, "Not found")

    def handle_analyze(self) -> None:
        content_type = self.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            self.send_error(400, "Use multipart/form-data")
            return
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        item = form["video"] if "video" in form else None
        if item is None or not getattr(item, "filename", ""):
            self.send_error(400, "Missing video file")
            return
        safe_name = Path(item.filename).name
        upload_path = PATHS.uploads / safe_name
        with upload_path.open("wb") as handle:
            shutil.copyfileobj(item.file, handle)
        try:
            report = analyze_video(upload_path, PATHS)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        self.send_json({"ok": True, "report": report})

    def send_file(self, path: Path, download: bool = False) -> None:
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            self.send_error(404, "Not found")
            return
        allowed_roots = [STATIC.resolve(), PATHS.reports.resolve(), PATHS.exports.resolve()]
        if not any(str(resolved).startswith(str(root)) for root in allowed_roots):
            self.send_error(403, "Forbidden")
            return
        if not resolved.exists() or not resolved.is_file():
            self.send_error(404, "Not found")
            return
        mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{resolved.name}"')
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")


def main() -> None:
    for folder in [PATHS.uploads, PATHS.reports, PATHS.exports]:
        folder.mkdir(parents=True, exist_ok=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Video Score Analyzer running at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server.serve_forever()


if __name__ == "__main__":
    main()
