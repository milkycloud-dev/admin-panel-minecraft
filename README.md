# Minecraft Admin Panel 🛠️

Minecraft Admin Panel is a standalone, lightweight, and fast GUI utility designed to manage remote Minecraft servers and web resources via SSH. It provides a simple "Apple-style" interface to sync mods, execute console commands, and manage server backups securely without relying on heavy web panels.

## Features ✨

* **📦 Mod Synchronization Hub**: Easily compare local and remote mods (`.jar` files) and synchronize them across your client download servers and the main game server.
* **💻 Interactive Console**: Connect directly to your server's `screen` session. Monitor live logs and execute commands as if you were in the terminal.
* **💾 Server Backups**: Create `7z` backups of your server with one click, automatically ignoring heavy or unnecessary folders (like Dynmap, CoreProtect, Logs).
* **🔄 Auto-Updater**: The application updates itself automatically from GitHub releases.
* **🛡️ White-Label & Secure**: No hardcoded IPs or credentials. All configurations are stored locally in your `admin_settings.json`.

## Quick Start 🚀

1. **Download**: Grab the latest `AdminPanel.exe` from the [Releases](https://github.com/milkycloud-dev/admin-panel-minecraft/releases) page.
2. **Launch**: Run the executable. On the first launch, you will be prompted to generate an empty configuration file or import an existing one.
3. **Configure**: Go to the **Settings (Настройки)** tab and enter your SSH credentials for your Game Server and Client Download Server.
4. **Restart**: Restart the application to apply the new settings.

### Configuration (`admin_settings.json`)

The application generates an `admin_settings.json` file in the same directory as the executable. It looks like this:

```json
{
    "client_server": {
        "name": "Web Server (Mods)",
        "host": "YOUR_IP",
        "user": "root",
        "password": "YOUR_PASSWORD",
        "remote_dir": "/var/www/mods"
    },
    "game_server": {
        "name": "Minecraft Server",
        "host": "YOUR_IP",
        "user": "root",
        "password": "YOUR_PASSWORD",
        "remote_dir": "/root/minecraft",
        "screen_name": "minecraft_screen_session_name"
    },
    "paths": {
        "local_mods_dir": "mods"
    },
    "backups": {
        "excluded_folders": "bluemap, dynmap, coreprotect, logs, crash-reports, cache, backups",
        "7z_args": "-mx9 -mmt4"
    }
}
```

## Screenshots 📸

*(Coming soon! Upload screenshots to the repository and link them here).*

## Building from Source 🛠️

To compile the executable yourself on Windows:

1. Clone the repository:
   ```bash
   git clone https://github.com/milkycloud-dev/admin-panel-minecraft.git
   cd admin-panel-minecraft
   ```
2. Install dependencies:
   ```bash
   pip install paramiko blake3 customtkinter Pillow
   ```
3. Compile using PyInstaller:
   ```bash
   python -m PyInstaller --onefile --noconfirm --windowed --icon "icon.png" --add-data "fonts;fonts" --add-data "icon.png;." -n AdminPanel main.py
   ```
4. The executable will be generated in the `dist/` directory.

## License 📄

This project is licensed under a standard open-source license. Feel free to fork and customize it for your own Minecraft projects!
