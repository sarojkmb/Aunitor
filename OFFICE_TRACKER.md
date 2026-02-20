# In Office Tracker

A small desktop app for self-attendance with a minimal UI.

## What it does
- Monitors current Wi-Fi SSID.
- Auto-marks today's attendance when connected to **`bbsrbdk wifi`**.
- Allows manual attendance log for the day.
- Shows month-wise office-day counts.

Attendance is stored locally in `attendance.db` next to `office_tracker.py`.

## Run manually
```bash
python3 office_tracker.py
```

## Run at laptop startup

### Windows (Task Scheduler)
1. Open **Task Scheduler** → **Create Basic Task**.
2. Trigger: **When I log on**.
3. Action: **Start a program**.
4. Program/script: `python` (or full python.exe path).
5. Add arguments: full path to `office_tracker.py`.
6. Finish and enable task.

### Linux (systemd user service)
Create `~/.config/systemd/user/office-tracker.service`:
```ini
[Unit]
Description=In Office Tracker

[Service]
ExecStart=/usr/bin/python3 /full/path/to/office_tracker.py
Restart=on-failure

[Install]
WantedBy=default.target
```

Then run:
```bash
systemctl --user daemon-reload
systemctl --user enable --now office-tracker.service
```

### macOS (Login Items)
- Add Terminal/iTerm profile command to run:
  `python3 /full/path/to/office_tracker.py`
- Add that app/profile under **System Settings → General → Login Items**.

## Notes
- Wi-Fi name matching is case-insensitive.
- If OS Wi-Fi tooling is missing, manual logging still works.
