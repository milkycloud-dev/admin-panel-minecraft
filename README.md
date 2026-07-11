<div align="center">
  <img src="icon.png" alt="Minecraft Admin Panel" width="128"/>
  
  # Minecraft Admin Panel
  **Professional Administration Solution for Minecraft Servers**
  
  [![Release](https://img.shields.io/github/v/release/milkycloud-dev/admin-panel-minecraft?style=for-the-badge&color=0078D4)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-brightgreen?style=for-the-badge)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![UI](https://img.shields.io/badge/UI-Flet_Framework-blue?style=for-the-badge)](https://flet.dev)

  *[Читать на русском](README_ru.md)*
</div>

---

**Minecraft Admin Panel** is a desktop application designed to optimize and automate Minecraft server management processes. The application architecture is built on the **Flet** (Flutter) framework, which ensures cross-platform compatibility, high responsiveness, and a modern user interface.

## Key Features

- **Automated Mod Deployment:** Direct integration via the SFTP protocol provides automatic file synchronization (removing outdated and uploading new mod versions).
- **Integrated RCON Console:** Secure remote server management through a built-in terminal featuring command history and syntax highlighting for system logs.
- **Backup Module:** Local data archiving using 7-Zip with support for dynamic directory exclusions (e.g., `world` or `logs`) to minimize storage load.
- **Optimized Build:** Binary files for Windows and Linux environments undergo extreme compression using the UPX algorithm, ensuring high portability and minimal executable size.
- **Update Delivery System:** An integrated automatic version verification module provides seamless application updates directly from the GitHub repository.

## Encrypted Launcher Manifest (V2.1)

Since launcher V2.1 the panel builds a SINGLE encrypted manifest at `/cloud/manifest.json`
(AES-256-GCM encryption + Ed25519 signature) instead of the plaintext `client/index.json`.
The "Собрать Manifest" button rebuilds the mod list on the server, then encrypts and signs
the manifest LOCALLY (the private key never leaves your machine) and uploads the envelope.

Where to provide the keys: **Settings -> Ключи manifest (V2.1)** — specify paths to two
local files with base64 keys:

- symmetric AES-256 key file (`manifest_sym.key`);
- private Ed25519 signing key file (`ed25519_private.key`).

Key VALUES are never stored in this repository or in CI. Generate a key set with:

```bash
python manifest_crypto.py gen
```

Local dry-run (without uploading):

```bash
python manifest_builder.py --index path/to/index.json --metadata cloud_manifest_metadata.json --out /tmp/manifest.json --sym-key-file /path/manifest_sym.key --priv-key-file /path/ed25519_private.key
```

## GitHub → fallback server mirror

GitHub is the source of truth; `download.inflexus.world` is the fallback when GitHub is
blocked. On startup the panel checks, and the **Синхр. GH→сервер** button syncs:

- Raw repo files: `settings.json`, `news.json`, `cloud/manifest.json`
  (server bridge `manifest.json` / `new/manifest.json` stay server-managed with
  `/cloud/exe-mirror` update URLs);
- Latest release assets: `NoteBuns-Portable-*.exe` and `NoteBuns_*.AppImage` →
  `/cloud/exe-mirror`.

Game payloads (mods / java / archives) already live under `/cloud/` on the server and are
not mirrored from GitHub (they are not in the public repo).

## Deployment and Configuration

The application is distributed as a compiled executable file and requires no installation. All configuration data is stored locally in the `admin_settings.json` file, which is generated automatically upon the first launch.

### Infrastructure Requirements
- Operating System: Windows 10/11 (64-bit) or modern Linux distributions.
- Installed 7-Zip archiver (adding it to the `PATH` system variable is recommended) for the backup module to function correctly.
- SSH/SFTP accessibility on the target server for file synchronization.

### Build from Source Instructions

To manually compile the executable file, a Python 3.11+ environment is required.

1. Clone the repository:
```bash
git clone https://github.com/milkycloud-dev/admin-panel-minecraft.git
cd admin-panel-minecraft
```

2. Install the necessary dependencies:
```bash
pip install -r requirements.txt
```

3. Build using `flet pack`. To optimize the size, it is recommended to exclude unused modules:
```bash
flet pack main.py --name AdminPanel-Windows --icon "icon.png" --add-data "icon.png;." -y --exclude-module numpy --exclude-module pandas --exclude-module PIL --exclude-module tkinter
```
Upon completion of the compilation process, the ready binary file will be available in the `dist` directory.

## Technology Stack
- **Core:** Python 3.11+
- **UI:** Flet Framework (Flutter)
- **Networking:** Paramiko (SFTP/SSH)
- **Compilation:** PyInstaller & UPX
- **Encryption:** Blake3 (update integrity verification)

---
<div align="center">
  <i>Solution for efficient Minecraft infrastructure management.</i>
</div>
