<div align="center">
  <img src="icon.png" alt="Minecraft Admin Panel" width="128"/>

  # Minecraft Admin Panel
  **Профессиональное решение для администрирования серверов Minecraft**<br/>
  **Professional Administration Solution for Minecraft Servers**

  [![Release](https://img.shields.io/github/v/release/milkycloud-dev/admin-panel-minecraft?style=for-the-badge&color=0078D4)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-brightgreen?style=for-the-badge)](https://github.com/milkycloud-dev/admin-panel-minecraft/releases)
  [![UI](https://img.shields.io/badge/UI-Flet_Framework-blue?style=for-the-badge)](https://flet.dev)
</div>

---

**Minecraft Admin Panel** — десктопное приложение на **Flet** (Flutter) для управления Minecraft-серверами: кроссплатформенность, быстрый отклик, современный UI.

**Minecraft Admin Panel** is a desktop app on **Flet** (Flutter) for Minecraft server management: cross-platform, responsive, modern UI.

## Ключевые возможности / Key Features

- **Автодеплой модов / Automated Mod Deployment:** SFTP-синхронизация (удаление старых, загрузка новых версий).
- **Консоль RCON / Integrated RCON Console:** удалённое управление, история команд, подсветка логов.
- **Бэкапы / Backup Module:** архивация через 7-Zip с исключениями каталогов (`world`, `logs`, …).
- **Сборка / Optimized Build:** Windows/Linux бинарники со сжатием UPX.
- **Автообновление / Update Delivery:** проверка и установка обновлений панели с GitHub.

## Зашифрованный manifest лаунчера (V2.1) / Encrypted Launcher Manifest

С V2.1 панель собирает **один** зашифрованный `/cloud/manifest.json` (AES-256-GCM + Ed25519) вместо открытого `client/index.json`. Кнопка «Собрать Manifest» пересобирает список модов на сервере, затем шифрует и подписывает файл **локально** (приватный ключ не покидает машину).

Since launcher V2.1 the panel builds a **single** encrypted `/cloud/manifest.json` (AES-256-GCM + Ed25519) instead of plaintext `client/index.json`. The “Собрать Manifest” button rebuilds the mod list on the server, then encrypts and signs **locally** (private key never leaves your machine).

Ключи / keys: **Настройки → Ключи manifest (V2.1)** — пути к двум локальным base64-файлам:

- `manifest_sym.key` (AES-256);
- `ed25519_private.key` (подпись).

Значения ключей в репозиторий и CI **не** кладутся. Генерация:

```bash
python manifest_crypto.py gen
```

Локальная проверка сборки без загрузки / local dry-run (no upload):

```bash
python manifest_builder.py --index path/to/index.json --metadata cloud_manifest_metadata.json --out /tmp/manifest.json --sym-key-file /path/manifest_sym.key --priv-key-file /path/ed25519_private.key
```

## Зеркало GitHub → fallback-сервер / GitHub → fallback server mirror

GitHub — источник правды; `download.inflexus.world` — запасной канал, если GitHub недоступен. При старте панель проверяет, кнопка **«Синхр. GH→сервер»** дозаливаёт:

GitHub is the source of truth; `download.inflexus.world` is the fallback when GitHub is blocked. On startup the panel checks; **«Синхр. GH→сервер»** syncs:

- raw: `settings.json`, `news.json`, `cloud/manifest.json`  
  (мосты `manifest.json` / `new/` на сервере со ссылками на `/cloud/exe-mirror`);
- релизные / release assets: `NoteBuns-Portable-*.exe`, `NoteBuns_*.AppImage` → `/cloud/exe-mirror`.

Игровые архивы / моды / Java живут в `/cloud/` на сервере и с GitHub не зеркалятся  
(Game payloads under `/cloud/` are not mirrored from GitHub — they are not in the public repo).

## Развертывание / Deployment

Приложение — готовый exe/бинарь без установки. Конфиг локально в `admin_settings.json` (создаётся при первом запуске).

Distributed as a compiled binary; no install. Config lives in local `admin_settings.json` (created on first launch).

### Требования / Requirements

- Windows 10/11 (64-bit) или современный Linux / modern Linux.
- 7-Zip в `PATH` (для бэкапов / for backups).
- SSH/SFTP до целевого сервера / to the target server.

### Сборка из исходников / Build from source

Python 3.11+:

```bash
git clone https://github.com/milkycloud-dev/admin-panel-minecraft.git
cd admin-panel-minecraft
pip install -r requirements.txt
flet pack main.py --name AdminPanel-Windows --icon "icon.png" --add-data "icon.png;." -y --exclude-module numpy --exclude-module pandas --exclude-module PIL --exclude-module tkinter
```

Готовый файл — в `dist/` / output in `dist/`.

## Стек / Technology Stack

- **Ядро / Core:** Python 3.11+
- **UI:** Flet (Flutter)
- **Сеть / Networking:** Paramiko (SFTP/SSH)
- **Сборка / Compilation:** PyInstaller & UPX
- **Хэши / Hashing:** Blake3
- **Крипто manifest / Manifest crypto:** AES-256-GCM + Ed25519 (`cryptography`)

---

<div align="center">
  <i>Решение для эффективного управления инфраструктурой Minecraft.<br/>
  Solution for efficient Minecraft infrastructure management.</i>
</div>
