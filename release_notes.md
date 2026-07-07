# Release 2.0.0

### Features
* Mod sync between client download host and game server with status comparison
* SSH console, server start/stop/restart via screen
* Remote backups with progress monitoring
* Config auto-discovery (Desktop, Downloads, app folder)
* Import/export settings, first-run import dialog
* Flet 0.85+ compatibility (Button, PopupMenuItem, padding, FilePicker services API)
* Thread-safe system log and UI updates
* Index builder: rebuilds `client/index.json` for NoteBuns launcher (b3: hashes)
* Creates `client/index.json` from built-in template if file is missing
* `run.cmd` — zero-install launcher; `tools/build_personal_runner.py` for personal copy

### Fixes (latest)
* Index rebuild works without existing `client/index.json`
* Red confirmation warning before index rebuild
* Repository cleanup: removed unused fonts, dev scripts, duplicate assets

### Upgrade
Download `AdminPanel-Windows.exe` or `AdminPanel-Linux` from this release.
