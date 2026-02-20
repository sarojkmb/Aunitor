# In Office Tracker

A small attendance app with a minimal web UI (opened from Python, no Tkinter required).

## Why this version
Some Python/Tk builds on macOS can crash with version errors. This app avoids Tkinter and uses a local browser UI instead.

## What it does
- Detects current Wi-Fi SSID.
- Auto-marks today's attendance when connected to **`bbsrbdk wifi`**.
- Allows manual attendance log for today.
- Shows month-wise office-day totals.

Attendance is stored in local SQLite file: `attendance.db`.

## Run
```bash
python3 office_tracker.py
```
Then open `http://127.0.0.1:8765/` if browser doesn’t auto-open.

## Optional flags
```bash
python3 office_tracker.py --port 9000 --no-browser
```

## Run on laptop startup

### Windows (Task Scheduler)
- Trigger: **When I log on**.
- Action: Start program `python`.
- Arguments: full path to `office_tracker.py --no-browser`.

### Linux (systemd user service)
`~/.config/systemd/user/office-tracker.service`
```ini
[Unit]
Description=In Office Tracker

[Service]
ExecStart=/usr/bin/python3 /full/path/to/office_tracker.py --no-browser
Restart=on-failure

[Install]
WantedBy=default.target
```
Enable:
```bash
systemctl --user daemon-reload
systemctl --user enable --now office-tracker.service
```

### macOS (LaunchAgent)
Create `~/Library/LaunchAgents/com.office.tracker.plist` to run this command at login:
```bash
/usr/bin/python3 /full/path/to/office_tracker.py --no-browser
```
(Use your preferred method for LaunchAgent creation/loading.)

## Notes
- Wi-Fi matching is case-insensitive.
- If OS Wi-Fi tools are unavailable, manual logging still works.
