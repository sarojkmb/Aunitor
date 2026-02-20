#!/usr/bin/env python3
"""In-office attendance tracker with Wi-Fi verification and a minimal Tkinter UI."""

from __future__ import annotations

import datetime as dt
import platform
import re
import sqlite3
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

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
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
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

    def close(self) -> None:
        self.conn.close()

    def mark_day(self, day: dt.date, mode: str, ssid: str | None) -> bool:
        now = dt.datetime.now().isoformat(timespec="seconds")
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
        cur = self.conn.execute("SELECT 1 FROM attendance WHERE date = ?", (day.isoformat(),))
        return cur.fetchone() is not None

    def month_summary(self) -> list[tuple[str, int]]:
        cur = self.conn.execute(
            """
            SELECT substr(date, 1, 7) AS month, COUNT(*) AS days
            FROM attendance
            GROUP BY month
            ORDER BY month DESC
            """
        )
        return [(month, days) for month, days in cur.fetchall()]


class OfficeTrackerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("In Office Tracker")
        self.root.geometry("560x480")
        self.root.configure(bg="#f5f7fb")
        self.store = AttendanceStore(DB_PATH)

        self.status_var = tk.StringVar(value="Checking Wi-Fi...")
        self.today_var = tk.StringVar(value="Today's attendance: --")
        self.target_var = tk.StringVar(value=f"Target Wi-Fi: {TARGET_WIFI}")

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="In Office Tracker", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(container, text="Minimal attendance monitor", foreground="#6b7280")
        subtitle.pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(container, padding=12)
        card.pack(fill="x")

        ttk.Label(card, textvariable=self.target_var).pack(anchor="w")
        ttk.Label(card, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 0))
        ttk.Label(card, textvariable=self.today_var).pack(anchor="w", pady=(8, 0))

        action_bar = ttk.Frame(container)
        action_bar.pack(fill="x", pady=12)

        ttk.Button(action_bar, text="Refresh Wi-Fi", command=self.refresh).pack(side="left")
        ttk.Button(action_bar, text="Log Today Manually", command=self.log_manual).pack(side="left", padx=8)

        ttk.Label(container, text="Attendance by month", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(4, 8))

        self.tree = ttk.Treeview(container, columns=("month", "days"), show="headings", height=10)
        self.tree.heading("month", text="Month")
        self.tree.heading("days", text="Days in office")
        self.tree.column("month", width=140, anchor="w")
        self.tree.column("days", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh(self) -> None:
        ssid = get_current_ssid()
        today = dt.date.today()
        target_matched = (ssid or "").strip().lower() == TARGET_WIFI.lower()

        if target_matched:
            inserted = self.store.mark_day(today, "auto", ssid)
            auto_status = "Attendance logged for today" if inserted else "Already logged today"
            self.status_var.set(f"Connected to '{ssid}' ✅ ({auto_status})")
        elif ssid:
            self.status_var.set(f"Connected to '{ssid}' ❌ (target not matched)")
        else:
            self.status_var.set("Wi-Fi not detected ❌")

        attendance_state = "Marked" if self.store.has_day(today) else "Not marked"
        self.today_var.set(f"Today's attendance: {attendance_state}")
        self._load_summary()

    def log_manual(self) -> None:
        today = dt.date.today()
        inserted = self.store.mark_day(today, "manual", get_current_ssid())
        if inserted:
            messagebox.showinfo("Logged", "Today's office attendance has been logged manually.")
        else:
            messagebox.showinfo("Already Logged", "Attendance for today is already present.")
        self.refresh()

    def _load_summary(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

        for month, days in self.store.month_summary():
            self.tree.insert("", "end", values=(month, days))

    def on_close(self) -> None:
        self.store.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    OfficeTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
