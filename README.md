# NoteBuns Admin Panel

## Overview

The NoteBuns Admin Panel is a proprietary, standalone graphical user interface (GUI) application designed for the centralized management of remote game servers and associated web resources via the SSH protocol. This utility provides an efficient interface for synchronizing modifications, executing remote commands, and performing secure server backups without the overhead of traditional web-based control panels.

## Key Capabilities

* **Modification Synchronization Framework**: A robust system for comparing local modification files (.jar) against remote counterparts, enabling automated, differential synchronization across multiple nodes, including client download servers and primary game instances.
* **Integrated Remote Console**: Secure shell (SSH) integration allows direct connection to active server processes (e.g., `screen` sessions). Administrators can monitor live output and issue commands in real-time.
* **Automated Backup Operations**: Facilitates the creation of highly compressed archives (7z format) of the server directory, featuring a configurable exclusion list to prevent the archiving of temporary or excessively large directories (e.g., logs, caches).
* **Self-Updating Architecture**: The application incorporates an automated update mechanism that interfaces directly with the official GitHub release pipeline, ensuring the software remains current with minimal administrative intervention.
* **Secure Configuration Management**: All authentication credentials and operational parameters are stored securely within a local configuration file (`admin_settings.json`), preventing the inclusion of sensitive data within the source code.

## Deployment Guidelines

1. **Acquisition**: Download the latest compiled binary (`AdminPanel.exe` for Windows, `AdminPanel` for Linux) from the official Releases page.
2. **Initialization**: Execute the binary. During the initial launch, the system will prompt the user to initialize a blank configuration matrix or import an existing JSON configuration file.
3. **Configuration**: Navigate to the Settings tab to input the requisite SSH credentials and directory paths for the remote host environments.
4. **Application**: Restart the application instance to validate and apply the newly configured parameters.

### Configuration Specification (`admin_settings.json`)

The application leverages a JSON-formatted configuration file generated in the working directory. A typical configuration structure is outlined below:

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

## Build Instructions

For internal compilation and deployment, the following procedure is required:

1. Clone the proprietary repository:
   ```bash
   git clone https://github.com/milkycloud-dev/admin-panel-minecraft.git
   cd admin-panel-minecraft
   ```
2. Provision the Python environment with required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute the PyInstaller build sequence:
   ```bash
   python -m PyInstaller --onefile --noconfirm --windowed --icon "icon.png" --add-data "fonts;fonts" --add-data "icon.png;." -n AdminPanel main.py
   ```

## Licensing Information

This software is distributed under a strictly proprietary license. Commercial use, reproduction, modification, and unauthorized distribution are strictly prohibited. Refer to the `LICENSE` file for detailed terms and conditions. Copyright (c) MilkyCloud. All Rights Reserved.
