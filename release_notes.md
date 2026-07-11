# Release 2.1.0

### Features
* Unified encrypted `/cloud/manifest.json` (AES-256-GCM + Ed25519), signed locally
* GitHub → fallback server mirror: `settings.json`, `news.json`, `cloud/manifest.json`, release exe/AppImage
* Startup auto-check + «Синхр. GH→сервер» button
* Key paths in Settings (values never stored in the repo)

### Fixes
* Remote mod scan retries up to 3 times with detailed system-log errors (host/path/cause)
* SSH connect timeout 20s + keepalive (fewer false failures on flaky download host)
* Default client mods path: `cloud/mods`

### Upgrade
Download `AdminPanel-Windows.exe` or `AdminPanel-Linux` from this release.
