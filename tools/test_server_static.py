"""Tests of the hub server's page route: "/" -> web/index.html and the page files under /css/, /js/, /vendor/.

Usage:   python tools/test_server_static.py        (or: python -m unittest tools.test_server_static -v)
Starts the server in this process on a free port with an empty temporary data folder: it never touches
data/, never starts or talks to a Chrome and never uses the ports of a running hub.
Checks:
  - "/" and "/index.html" serve index.html; .js/.css files with the right MIME type and charset, read fresh from disk
  - Cache-Control: no-cache + ETag "<mtime_ns>-<size>" + X-Content-Type-Options: nosniff; If-None-Match -> 304
  - the page itself (index.html, also its 304) carries Content-Security-Policy (only own scripts, no framing) and
    X-Frame-Options: DENY; the .js/.css files and the API do not
  - path traversal and tricks (.., %-encoded and double-encoded, backslashes, drive letters, NUL, trailing dot/space,
    alternate data streams, Windows device names, encoded "/") -> 404, without leaking any file content
  - only .js/.css: .md, .txt, .html, folders and missing files -> 404
  - the Host check (DNS-rebinding protection) runs first: wrong or missing Host -> 403
  - the JSON API still answers next to the page route
"""
from __future__ import annotations

import http.client
import json
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_hub import server  # noqa: E402

WEB = server.WEB


class StaticRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.httpd = server.Server(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        server.Handler.config = {"domain": "https://www.vinted.lu", "data_folder": cls.tmp.name,
                                 "hub_port": cls.port, "chrome_port": 9599}
        server.Handler.allowed_hosts = {f"127.0.0.1:{cls.port}", f"localhost:{cls.port}"}
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    # raw request: the path goes out exactly as written (no client-side normalisation of "..")
    def get(self, path, host="default", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
        if host == "default":
            host = f"127.0.0.1:{self.port}"
        if host is not None:
            conn.putheader("Host", host)
        for k, v in (headers or {}).items():
            conn.putheader(k, v)
        conn.endheaders()
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, body

    def assert_page_file(self, path, file, mime):
        status, headers, body = self.get(path)
        self.assertEqual(status, 200, path)
        self.assertEqual(headers["content-type"], f"{mime}; charset=utf-8", path)
        self.assertEqual(headers["cache-control"], "no-cache", path)
        self.assertEqual(headers["x-content-type-options"], "nosniff", path)
        st = file.stat()
        self.assertEqual(headers["etag"], f'"{st.st_mtime_ns}-{st.st_size}"', path)
        self.assertEqual(body, file.read_bytes(), path)
        return headers

    def test_index(self):
        for path in ("/", "/index.html", "/?x=1"):
            self.assert_page_file(path, WEB / "index.html", "text/html")
        self.assertIn(b'<div id="app">', self.get("/")[2])

    def test_page_files_and_mime_types(self):
        files = sorted(p for p in WEB.rglob("*") if p.is_file() and p.suffix in (".js", ".css")
                       and p.relative_to(WEB).parts[0] in server.STATIC_DIRS)
        self.assertGreater(len(files), 10)
        for file in files:
            url = "/" + file.relative_to(WEB).as_posix()
            self.assert_page_file(url, file, "text/javascript" if file.suffix == ".js" else "text/css")
        self.assert_page_file("/vendor/preact-htm.js?v=2", WEB / "vendor" / "preact-htm.js", "text/javascript")
        # an encoded character in a file name is decoded ("%2D" = "-")
        self.assert_page_file("/vendor/preact%2Dhtm.js", WEB / "vendor" / "preact-htm.js", "text/javascript")

    def test_revalidation(self):
        etag = self.get("/js/i18n.js")[1]["etag"]
        status, headers, body = self.get("/js/i18n.js", headers={"If-None-Match": etag})
        self.assertEqual((status, body), (304, b""))
        self.assertEqual(headers["etag"], etag)
        self.assertEqual(self.get("/js/i18n.js", headers={"If-None-Match": '"0-0"'})[0], 200)
        status, _, body = self.get("/", headers={"If-None-Match": self.get("/")[1]["etag"]})
        self.assertEqual((status, body), (304, b""))

    def test_page_security_headers(self):
        csp_parts = ["default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline'", "img-src 'self' data:",
                     "connect-src 'self'", "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'"]
        for path in ("/", "/index.html", "/?x=1"):
            with self.subTest(path=path):
                status, headers, _ = self.get(path)
                self.assertEqual(status, 200)
                csp = headers.get("content-security-policy", "")
                self.assertEqual(sorted(p.strip() for p in csp.split(";")), sorted(csp_parts), csp)
                self.assertNotIn("unsafe-eval", csp)
                self.assertEqual(headers.get("x-frame-options"), "DENY")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
        # also on a revalidation (304) of the page
        status, headers, _ = self.get("/", headers={"If-None-Match": self.get("/")[1]["etag"]})
        self.assertEqual(status, 304)
        self.assertIn("frame-ancestors 'none'", headers.get("content-security-policy", ""))
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        # the page has no inline script that the policy would block (every <script> has a src)
        page = (WEB / "index.html").read_text(encoding="utf-8")
        scripts = page.count("<script")
        self.assertEqual(scripts, page.count("<script src=") + page.count('<script type="module" src='), "inline <script> in index.html")
        self.assertIsNone(re.search(r"\son[a-z]+\s*=", page, re.I), "inline event handler attribute in index.html")
        # only the page: module/style files, the API and errors stay as they are
        for path in ("/js/app.js", "/css/base.css", "/vendor/preact-htm.js", "/api/version", "/js/nonexistent.js"):
            with self.subTest(path=path):
                headers = self.get(path)[1]
                self.assertNotIn("content-security-policy", headers, path)
                self.assertNotIn("x-frame-options", headers, path)

    def test_traversal_and_tricks_are_404(self):
        paths = [
            # leaving web/<dir>
            "/js/../server.py", "/js/../../config.json", "/js/../../vinted_hub/server.py", "/css/../index.html",
            "/vendor/../index.html", "/web/../server.py", "/web/../../config.json", "/js/./i18n.js", "/js/..",
            # %-encoded, mixed case, double-encoded
            "/js/%2e%2e/server.py", "/js/%2E%2E/%2E%2E/config.json", "/js/.%2e/server.py", "/js/%2e./server.py",
            "/js/..%2fserver.py", "/js/..%2Fserver.py", "/css/..%2F..%2Fserver.py", "/js/%2e%2e%2f%2e%2e%2fconfig.json",
            "/js/%252e%252e/server.py", "/js/%252e%252e%252fserver.py", "/js/state%2fstore.js",
            # backslashes (Windows separators), raw and encoded
            "/js/..%5cserver.py", "/js/..%5C..%5Cconfig.json", "/js/%2e%2e%5cserver.py", "/js\\..\\server.py",
            "/js/state\\store.js", "/js/state%5cstore.js",
            # drive letters, absolute paths, UNC, alternate data streams
            "/js/C:%5cWindows%5cwin.ini", "/js/C:/Windows/win.ini", "/js//C:/Windows/win.ini", "/js/%2f%2fserver/share/x.js",
            "/js/i18n.js::$DATA", "/js/i18n.js%3A%3A%24DATA", "/js/i18n.js:x.js",
            # NUL, trailing dot/space (Windows strips them), device names
            "/js/%00.js", "/js/i18n.js%00.css", "/js/i18n.js%00", "/js/i18n.js.", "/js/i18n.js%20", "/js/i18n.js%2e",
            "/js/i18n.js...", "/js/CON.js", "/js/nul.css", "/js/aux", "/css/com1.css", "/js/lpt9.js", "/js/...",
            # wrong place, wrong type, folders, missing
            "/vendor/LICENSES.md", "/vendor/LICENSE-htm.txt", "/hub.html", "/web/index.html", "/web/hub.html", "/index.htm",
            "/js/", "/js", "/css", "/vendor/", "/js//i18n.js", "/js/i18n", "/js/state", "/js/state/", "/css/base.css/",
            "/js/nonexistent.js", "/js/i18n.js/x.js", "/server.py", "/vinted_hub/server.py", "/config.json", "/data/listings.json",
            "/JS/i18n.js", "/%6As/i18n.js", "/%2e%2e/config.json", "/js%2fi18n.js", "/tools/check_listing.py",
        ]
        secrets = [b"def static_path", b"hub_port", b"[fonts]", b"export function t("]
        for path in paths:
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 404, f"{path} -> {status} {body[:80]!r}")
                self.assertTrue(headers["content-type"].startswith("application/json"), path)
                self.assertIn("error", json.loads(body))
                for s in secrets:
                    self.assertNotIn(s, body, path)

    def test_host_check_runs_first(self):
        for path in ("/", "/index.html", "/js/i18n.js", "/css/base.css", "/js/../server.py", "/api/version"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path, host="evil.example")[0], 403)
                self.assertEqual(self.get(path, host=f"evil.example:{self.port}")[0], 403)
                self.assertEqual(self.get(path, host=f"127.0.0.1:{self.port + 1}")[0], 403)
                self.assertEqual(self.get(path, host=None)[0], 403)
        self.assertEqual(self.get("/js/i18n.js", host=f"localhost:{self.port}")[0], 200)

    def test_api_still_answers(self):
        status, headers, body = self.get("/api/version")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(json.loads(body), {"version": 0})
        status, _, body = self.get("/api/stats")
        self.assertEqual((status, json.loads(body)["history"]), (200, []))
        self.assertEqual(self.get("/api/nothing")[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
