#!/usr/bin/env python3
"""In-office attendance tracker with browser-based minimal UI (no Tk dependency)."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import platform
import re
import sqlite3
import subprocess
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TARGET_WIFI = "bbsrbdk wifi"
DB_PATH = Path(__file__).with_name("attendance.db")


def run_command(cmd: list[str]) -> str:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return (completed.stdout or "") + (completed.stderr or "")
    except Exception:
        return ""


def get_current_ssid() -> str | None:
    system = platform.system().lower()

    if "windows" in system:
        output = run_command(["netsh", "wlan", "show", "interfaces"])
        for line in output.splitlines():
            if "ssid" in line.lower() and "bssid" not in line.lower() and ":" in line:
                return line.split(":", 1)[1].strip() or None

    if "linux" in system:
        output = run_command(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
        for line in output.splitlines():
            if line.startswith("yes:"):
                return line.split(":", 1)[1].strip() or None

    if "darwin" in system:
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        output = run_command([airport, "-I"])
        for line in output.splitlines():
            match = re.match(r"\s*SSID:\s*(.+)", line)
            if match:
                return match.group(1).strip() or None

    return None


class AttendanceStore:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    date TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    ssid TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self.conn.commit()

    def mark_day(self, day: dt.date, mode: str, ssid: str | None) -> bool:
        now = dt.datetime.now().isoformat(timespec="seconds")
        with self.lock:
            try:
                self.conn.execute(
                    "INSERT INTO attendance (date, mode, ssid, created_at) VALUES (?, ?, ?, ?)",
                    (day.isoformat(), mode, ssid, now),
                )
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def has_day(self, day: dt.date) -> bool:
        with self.lock:
            cur = self.conn.execute("SELECT 1 FROM attendance WHERE date = ?", (day.isoformat(),))
            return cur.fetchone() is not None

    def month_summary(self) -> list[tuple[str, int]]:
        with self.lock:
            cur = self.conn.execute(
                """
                SELECT substr(date, 1, 7) AS month, COUNT(*) AS days
                FROM attendance
                GROUP BY month
                ORDER BY month DESC
                """
            )
            return [(month, days) for month, days in cur.fetchall()]


def evaluate_status(store: AttendanceStore) -> dict[str, str | bool | list[tuple[str, int]]]:
    ssid = get_current_ssid()
    today = dt.date.today()
    matched = (ssid or "").strip().lower() == TARGET_WIFI.lower()

    if matched:
        inserted = store.mark_day(today, "auto", ssid)
        wifi_status = f"Connected to '{ssid}' ✅"
        detail = "Attendance auto-logged today." if inserted else "Attendance already logged today."
    elif ssid:
        wifi_status = f"Connected to '{ssid}' ❌"
        detail = f"Target Wi-Fi is '{TARGET_WIFI}'."
    else:
        wifi_status = "Wi-Fi not detected ❌"
        detail = "Manual log is still available."

    today_marked = store.has_day(today)

    return {
        "wifi_status": wifi_status,
        "detail": detail,
        "today_status": "Marked" if today_marked else "Not marked",
        "summary": store.month_summary(),
    }


def render_page(data: dict[str, object], flash: str = "") -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(month))}</td><td>{days}</td></tr>"
        for month, days in data["summary"]
    )
    if not rows:
        rows = '<tr><td colspan="2">No attendance yet.</td></tr>'

    flash_html = f'<div class="flash">{html.escape(flash)}</div>' if flash else ""

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>In Office Tracker</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; background:#f5f7fb; margin:0; }}
.container {{ max-width:760px; margin:24px auto; padding:0 16px; }}
.card {{ background:white; border-radius:12px; padding:16px; box-shadow:0 4px 20px rgba(0,0,0,.05); margin-bottom:14px; }}
h1 {{ margin:0 0 6px; font-size:28px; }}
.sub {{ color:#667085; margin-bottom:10px; }}
.status {{ font-weight:600; margin:8px 0; }}
.meta {{ color:#475467; margin:0; }}
.actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
button {{ border:0; border-radius:10px; padding:10px 14px; cursor:pointer; font-weight:600; }}
.btn-primary {{ background:#1d4ed8; color:white; }}
.btn-secondary {{ background:#111827; color:white; }}
table {{ width:100%; border-collapse:collapse; background:white; border-radius:12px; overflow:hidden; }}
th, td {{ text-align:left; padding:12px; border-bottom:1px solid #eef2f7; }}
.flash {{ background:#ecfeff; border:1px solid #a5f3fc; color:#155e75; padding:10px 12px; border-radius:10px; margin-bottom:10px; }}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <h1>In Office Tracker</h1>
    <div class="sub">Minimal attendance monitor</div>
    {flash_html}
    <p class="meta">Target Wi-Fi: <strong>{html.escape(TARGET_WIFI)}</strong></p>
    <p class="status">{html.escape(str(data['wifi_status']))}</p>
    <p class="meta">{html.escape(str(data['detail']))}</p>
    <p class="meta">Today's attendance: <strong>{html.escape(str(data['today_status']))}</strong></p>
    <div class="actions">
      <form method="post" action="/refresh"><button class="btn-primary" type="submit">Refresh Wi-Fi</button></form>
      <form method="post" action="/manual"><button class="btn-secondary" type="submit">Log Today Manually</button></form>
    </div>
  </div>
  <table>
    <thead><tr><th>Month</th><th>Days in office</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    store: AttendanceStore

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        flash = parse_qs(parsed.query).get("m", [""])[0]
        data = evaluate_status(self.store)
        self._send_html(render_page(data, flash))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/manual":
            inserted = self.store.mark_day(dt.date.today(), "manual", get_current_ssid())
            msg = "Manually logged attendance for today." if inserted else "Attendance already logged today."
            self._redirect(f"/?m={msg}")
            return

        if parsed.path == "/refresh":
            self._redirect("/?m=Status refreshed.")
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def build_server(host: str, port: int, store: AttendanceStore) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (AppHandler,), {})
    handler.store = store
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="In-office attendance tracker")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    args = parser.parse_args()

    store = AttendanceStore(DB_PATH)
    server = build_server(args.host, args.port, store)
    url = f"http://{args.host}:{args.port}/"
    print(json.dumps({"status": "running", "url": url, "target_wifi": TARGET_WIFI}))

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
