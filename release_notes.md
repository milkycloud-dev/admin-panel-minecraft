# Release 2.0.0

### Features
* Mod sync between client download host and game server with status comparison
* SSH console, server start/stop/restart via screen
* Remote backups with progress monitoring
* Config auto-discovery (Desktop, Downloads, app folder)
* Import/export settings, first-run import dialog
* Flet 0.85+ compatibility (Button, PopupMenuItem, padding, FilePicker services API)
* Thread-safe system log and UI updates
* Index builder: rebuilds `client/index.json` (launcher mod list), not `manifest.json`
* Obsolete `manifest_manager.py` moved to `Old/` (launcher uses index via `index_urls`)
* `run.cmd` — zero-install launcher with fresh clone each run (settings preserved)
* `run_personal.cmd.example` — personal launcher template with embedded settings

### Upgrade
Download `AdminPanel-Windows.exe` or `AdminPanel-Linux` from this release.
