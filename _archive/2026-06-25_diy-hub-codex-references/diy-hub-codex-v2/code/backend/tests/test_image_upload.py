"""DIY-015 (Stage 13) — Manual image upload acceptance tests.

Verifies the new ``POST /api/components/<component_id>/image`` endpoint:

  1. multipart/form-data upload   -> 200, file on disk, component updated
  2. application/json URL paste   -> 200, file on disk, component updated
                                       (uses a small in-process HTTP server
                                       that serves a tiny PNG so the test
                                       runs offline and never touches the
                                       real internet)

Validation paths:

  3. bad extension               -> 400
  4. missing file/URL             -> 400
  5. nonexistent component id     -> 404
  6. unsupported Content-Type     -> 400

Why no ``fastapi.testclient``? It pulls in ``httpx``, which isn't a project
dependency (and the org rule for DIY-015 says: do NOT add new dependencies).
Instead we boot a real uvicorn server on a free port for the test's
duration and hit it with stdlib ``urllib``.

Run with:
    cd code/backend && .venv/bin/python -m unittest tests.test_image_upload -v
"""
from __future__ import annotations

import io
import os
import re
import socket
import sqlite3
import struct
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid
import zlib
from email.generator import BytesGenerator
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Make ``app`` importable when running from any cwd.
sys.path.insert(0, ".")

import uvicorn  # noqa: E402

from app.db import engine, get_db_path, get_images_dir  # noqa: E402
from app.main import app  # noqa: E402
from sqlalchemy import text  # noqa: E402


# -----------------------------------------------------------------------
# Tiny PNG fixture (1x1 transparent, ~70 bytes) — generated with stdlib.
# -----------------------------------------------------------------------

def _make_png_bytes() -> bytes:
    """Build a tiny but valid 1x1 transparent PNG."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    raw = b"\x00\x00\x00\x00\x00"  # filter byte + 4 zero RGBA bytes
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


VALID_PNG = _make_png_bytes()
assert VALID_PNG.startswith(b"\x89PNG\r\n\x1a\n"), "PNG fixture malformed"


# -----------------------------------------------------------------------
# Tiny HTTP server: serves VALID_PNG at /test.png so the URL test runs
# offline.
# -----------------------------------------------------------------------

class _OneShotPngServer:
    def __init__(self) -> None:
        self._httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self.port: int = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True
        )

    def __enter__(self) -> "_OneShotPngServer":
        self._thread.start()
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return self
            except OSError:
                pass
        raise RuntimeError("test PNG server failed to start")

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        finally:
            self._thread.join(timeout=2)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence stderr noise
        pass

    def do_GET(self):  # noqa: N802
        if self.path != "/test.png":
            self.send_response(404)
            self.end_headers()
            return
        body = VALID_PNG
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# -----------------------------------------------------------------------
# In-process uvicorn server — bound to a free port, started once per test
# class, hit with stdlib urllib.
# -----------------------------------------------------------------------

class _UvicornTestServer:
    """Run the real FastAPI app on a free localhost port for the test."""

    def __init__(self) -> None:
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,  # OS picks free port (we'll override below)
            log_level="warning",
            access_log=False,
            lifespan="off",  # no startup/shutdown events in tests
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, daemon=True
        )
        self.port: int = 0

    def __enter__(self) -> "_UvicornTestServer":
        # Reserve a free port up front so we can return it deterministically
        # even before uvicorn fully exposes its bound socket.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        self.port = probe.getsockname()[1]
        probe.close()
        # Reconfigure the config with the concrete port.
        self._server.config.port = self.port
        self._thread.start()
        # Wait for the server to bind.
        for _ in range(100):  # up to ~5s
            if self._server.started:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("uvicorn test server failed to start")
        # Verify it's actually accepting connections.
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError(f"uvicorn test server not accepting on port {self.port}")

    def __exit__(self, exc_type, exc, tb) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


# -----------------------------------------------------------------------
# stdlib HTTP client helpers — no httpx dependency.
# -----------------------------------------------------------------------

def _http_post(
    base_url: str,
    path: str,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(
        url=f"{base_url}{path}",
        data=body,
        method="POST",
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers or {})


def _build_multipart_body(
    fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    """Build a multipart/form-data body using stdlib ``email``.

    Returns ``(body_bytes, content_type_header)``. The ``content_type``
    includes the boundary and is what the server expects.
    """
    msg = MIMEMultipart("form-data")
    boundary = msg.get_boundary()
    # Strip default headers — we want a raw body, not a full RFC822 message.
    for k in list(msg.keys()):
        del msg[k]

    out = io.BytesIO()

    def _write(part_bytes: bytes) -> None:
        out.write(part_bytes)

    # Build raw parts.
    for name, value in fields.items():
        _write(f"--{boundary}\r\n".encode())
        _write(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        _write(value.encode("utf-8"))
        _write(b"\r\n")

    for name, (filename, content, ctype) in files.items():
        _write(f"--{boundary}\r\n".encode())
        _write(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        _write(f"Content-Type: {ctype}\r\n\r\n".encode())
        _write(content)
        _write(b"\r\n")

    _write(f"--{boundary}--\r\n".encode())

    body = out.getvalue()
    return body, f"multipart/form-data; boundary={boundary}"


# -----------------------------------------------------------------------
# Test DB helpers
# -----------------------------------------------------------------------

def _create_test_component(name: str = "Test Upload Component") -> int:
    """Insert a minimal component row directly via SQL and return its id."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO components (name, category, quantity, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """,
            (name, "Other", 1, "{}"),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def _cleanup_component(component_id: int) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM components WHERE id = :id"),
                {"id": component_id},
            )
    except Exception:  # noqa: BLE001
        pass


def _cleanup_image_files_for(component_id: int) -> None:
    images_dir = Path(get_images_dir())
    if not images_dir.exists():
        return
    for f in images_dir.glob(f"{component_id}-*.*"):
        try:
            f.unlink()
        except OSError:
            pass


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

class ImageUploadEndpointTests(unittest.TestCase):
    """End-to-end tests against POST /api/components/<id>/image."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _UvicornTestServer()
        cls.server.__enter__()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.__exit__(None, None, None)

    def setUp(self) -> None:
        # Use a unique name per test so DB lookups never collide if a
        # previous test's cleanup failed.
        self.component_id = _create_test_component(
            name=f"Upload Test {uuid.uuid4().hex[:8]}"
        )
        self.addCleanup(_cleanup_image_files_for, self.component_id)
        self.addCleanup(_cleanup_component, self.component_id)

    # ----- happy paths ------------------------------------------------

    def test_multipart_upload_succeeds(self):
        body, ctype = _build_multipart_body(
            fields={"source_url": "https://example.com/orig.jpg"},
            files={"image": ("test.png", VALID_PNG, "image/png")},
        )
        status, raw, _headers = _http_post(
            self.base_url,
            f"/api/components/{self.component_id}/image",
            body=body,
            headers={"Content-Type": ctype},
        )
        self.assertEqual(status, 200, raw)
        import json as _json
        data = _json.loads(raw)
        self.assertTrue(data.get("image_path"))
        self.assertEqual(data.get("image_source"), "user_uploaded")
        self.assertTrue(data.get("image_uploaded_at"))

        # File on disk?
        proj_root = Path(__file__).resolve().parents[3]
        abs_path = proj_root / data["image_path"]
        self.assertTrue(abs_path.exists(), f"file not on disk: {abs_path}")
        self.assertEqual(abs_path.read_bytes(), VALID_PNG)

        # Naming pattern: <id>-<uuid8>.png
        self.assertRegex(
            abs_path.name,
            re.compile(rf"^{self.component_id}-[0-9a-f]{{8}}\.png$"),
        )

        # Component row updated.
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT image_path, image_source, image_uploaded_at "
                    "FROM components WHERE id = :id"
                ),
                {"id": self.component_id},
            ).one()
        self.assertEqual(row[0], data["image_path"])
        self.assertEqual(row[1], "user_uploaded")
        self.assertTrue(row[2])

    def test_url_json_fetch_succeeds(self):
        with _OneShotPngServer() as srv:
            url = f"http://127.0.0.1:{srv.port}/test.png"
            payload = b'{"url": "' + url.encode() + b'"}'
            status, raw, _ = _http_post(
                self.base_url,
                f"/api/components/{self.component_id}/image",
                body=payload,
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(status, 200, raw)
        import json as _json
        data = _json.loads(raw)
        self.assertTrue(data.get("image_path"))
        self.assertEqual(data.get("image_source"), "user_url")
        self.assertTrue(data.get("image_uploaded_at"))

        proj_root = Path(__file__).resolve().parents[3]
        abs_path = proj_root / data["image_path"]
        self.assertTrue(abs_path.exists())
        self.assertEqual(abs_path.read_bytes(), VALID_PNG)

    # ----- validation -------------------------------------------------

    def test_bad_extension_is_rejected(self):
        body, ctype = _build_multipart_body(
            fields={},
            files={"image": ("not-an-image.txt", b"hello world", "text/plain")},
        )
        status, raw, _ = _http_post(
            self.base_url,
            f"/api/components/{self.component_id}/image",
            body=body,
            headers={"Content-Type": ctype},
        )
        self.assertEqual(status, 400, raw)
        import json as _json
        detail = _json.loads(raw).get("detail", "").lower()
        self.assertIn("extension", detail)

    def test_missing_file_on_multipart_is_rejected(self):
        body, ctype = _build_multipart_body(
            fields={"source_url": "https://example.com/x.jpg"},
            files={},  # no 'image' file part
        )
        status, raw, _ = _http_post(
            self.base_url,
            f"/api/components/{self.component_id}/image",
            body=body,
            headers={"Content-Type": ctype},
        )
        self.assertEqual(status, 400, raw)
        import json as _json
        detail = _json.loads(raw).get("detail", "").lower()
        self.assertIn("image", detail)

    def test_missing_url_on_json_is_rejected(self):
        status, raw, _ = _http_post(
            self.base_url,
            f"/api/components/{self.component_id}/image",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400, raw)
        import json as _json
        detail = _json.loads(raw).get("detail", "").lower()
        self.assertIn("url", detail)

    def test_unknown_component_is_404(self):
        body, ctype = _build_multipart_body(
            fields={},
            files={"image": ("test.png", VALID_PNG, "image/png")},
        )
        status, raw, _ = _http_post(
            self.base_url,
            "/api/components/999999999/image",
            body=body,
            headers={"Content-Type": ctype},
        )
        self.assertEqual(status, 404, raw)

    def test_unsupported_content_type_is_rejected(self):
        status, raw, _ = _http_post(
            self.base_url,
            f"/api/components/{self.component_id}/image",
            body=b"hello",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(status, 400, raw)
        import json as _json
        detail = _json.loads(raw).get("detail", "").lower()
        self.assertIn("content-type", detail)


if __name__ == "__main__":
    unittest.main()