"""
Зеркало GitHub -> fallback-сервер для всех файлов, с которыми работает лаунчер.

На GitHub всегда актуальная версия; на сервере — копия на случай, если GitHub
недоступен у игрока. Модуль:
  1. Raw-файлы репозитория (settings, news, bridge manifests, cloud/manifest).
  2. Ассеты последнего релиза (exe / AppImage) в /cloud/exe-mirror.

Сравнение: имя + размер (для raw — Content-Length vs st_size на SFTP).

GitHub -> fallback-server mirror for every file the launcher uses.
Raw repo files + latest release assets. Compare by size; download & SFTP upload if stale/missing.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from dataclasses import dataclass, field

GITHUB_API_LATEST = (
    "https://api.github.com/repos/milkycloud-dev/melody-launcher-minecraft/releases/latest"
)
GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/milkycloud-dev/melody-launcher-minecraft/main"
)
MIRROR_SUBPATH = "cloud/exe-mirror"

# Пути относительно корня репо (GitHub) == пути относительно remote_base_dir (сервер).
# Paths relative to repo root (GitHub) == paths relative to remote_base_dir (server).
# Файлы лаунчера с GitHub raw → копия на сервере.
# Мосты (manifest.json / new/manifest.json) НЕ синхронизируем с GitHub:
# на сервере в них стоят URL на /cloud/exe-mirror (апдейт без GitHub).
CONTENT_FILES = (
    "settings.json",
    "news.json",
    "cloud/manifest.json",
)

ASSET_MATCHERS = (
    lambda name: name.startswith("NoteBuns-Portable-") and name.endswith(".exe"),
    lambda name: name.startswith("NoteBuns_") and name.endswith(".AppImage"),
)


@dataclass
class MirrorStatus:
    tag: str = ""
    ok: bool = False
    message: str = ""
    missing: list = field(default_factory=list)
    synced: list = field(default_factory=list)
    content_ok: int = 0
    content_stale: int = 0
    assets_ok: int = 0
    assets_stale: int = 0


def _ua_request(url: str, method: str = "GET") -> urllib.request.Request:
    return urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": "NoteBuns-AdminPanel",
            "Accept": "application/vnd.github+json",
        },
    )


def fetch_latest_release() -> dict:
    with urllib.request.urlopen(_ua_request(GITHUB_API_LATEST), timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def pick_assets(release: dict) -> list[dict]:
    picked = []
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if any(match(name) for match in ASSET_MATCHERS):
            picked.append(asset)
    return picked


def _github_content_size(rel_path: str) -> int | None:
    url = f"{GITHUB_RAW_BASE}/{rel_path}"
    try:
        with urllib.request.urlopen(_ua_request(url, method="HEAD"), timeout=30) as resp:
            cl = resp.headers.get("Content-Length")
            if cl is not None:
                return int(cl)
        with urllib.request.urlopen(_ua_request(url), timeout=60) as resp:
            return len(resp.read())
    except Exception:
        return None


def _sftp_size(ssh_manager, remote_path: str) -> int | None:
    try:
        return int(ssh_manager.sftp.stat(remote_path).st_size)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def check_content_mirror(ssh_manager, remote_base_dir: str) -> MirrorStatus:
    """Проверить raw-файлы репозитория на сервере (без загрузки)."""
    status = MirrorStatus()
    base = remote_base_dir.rstrip("/")
    for rel in CONTENT_FILES:
        gh_size = _github_content_size(rel)
        if gh_size is None:
            status.missing.append({"kind": "content", "path": rel, "reason": "github_unavailable"})
            status.content_stale += 1
            continue
        remote_path = f"{base}/{rel}"
        remote_size = _sftp_size(ssh_manager, remote_path)
        if remote_size is None or remote_size != gh_size:
            status.missing.append(
                {
                    "kind": "content",
                    "path": rel,
                    "url": f"{GITHUB_RAW_BASE}/{rel}",
                    "github_size": gh_size,
                    "server_size": remote_size,
                }
            )
            status.content_stale += 1
        else:
            status.content_ok += 1

    status.ok = not status.missing
    status.message = (
        f"Контент актуален ({status.content_ok}/{len(CONTENT_FILES)})"
        if status.ok
        else f"Контент отстаёт: {status.content_stale}/{len(CONTENT_FILES)} файл(ов)"
    )
    return status


def check_mirror(ssh_manager, remote_base_dir: str) -> MirrorStatus:
    """Проверить только exe/AppImage зеркало релиза."""
    status = MirrorStatus()
    try:
        release = fetch_latest_release()
    except Exception as err:
        status.message = f"GitHub API недоступен: {err}"
        return status

    status.tag = release.get("tag_name", "")
    assets = pick_assets(release)
    if not assets:
        status.message = f"В релизе {status.tag} нет подходящих ассетов"
        return status

    mirror_dir = f"{remote_base_dir.rstrip('/')}/{MIRROR_SUBPATH}"
    for asset in assets:
        name = asset["name"]
        size = int(asset.get("size", 0))
        remote_path = f"{mirror_dir}/{name}"
        remote_size = _sftp_size(ssh_manager, remote_path)
        if remote_size is None or remote_size != size:
            status.missing.append(asset)
            status.assets_stale += 1
        else:
            status.assets_ok += 1

    status.ok = not status.missing
    status.message = (
        f"Exe-зеркало актуально ({status.tag})"
        if status.ok
        else f"Exe-зеркалу не хватает {len(status.missing)} файла(ов) релиза {status.tag}"
    )
    return status


def check_all(ssh_manager, remote_base_dir: str) -> MirrorStatus:
    """Полная проверка: raw-контент + релизные ассеты."""
    content = check_content_mirror(ssh_manager, remote_base_dir)
    assets = check_mirror(ssh_manager, remote_base_dir)

    status = MirrorStatus(
        tag=assets.tag,
        content_ok=content.content_ok,
        content_stale=content.content_stale,
        assets_ok=assets.assets_ok,
        assets_stale=assets.assets_stale,
        missing=list(content.missing) + list(assets.missing),
    )
    status.ok = not status.missing
    parts = [content.message]
    if assets.tag or assets.message:
        parts.append(assets.message)
    status.message = " | ".join(parts)
    return status


def sync_content_mirror(ssh_manager, remote_base_dir: str, progress_cb=None) -> MirrorStatus:
    def log(message: str):
        if progress_cb:
            progress_cb(message)

    status = check_content_mirror(ssh_manager, remote_base_dir)
    if status.ok or not status.missing:
        log(status.message)
        return status

    base = remote_base_dir.rstrip("/")
    for item in list(status.missing):
        if item.get("kind") != "content":
            continue
        rel = item["path"]
        url = item.get("url") or f"{GITHUB_RAW_BASE}/{rel}"
        log(f"Скачивание {rel} с GitHub...")
        try:
            with urllib.request.urlopen(_ua_request(url), timeout=120) as response:
                data = response.read()
            remote_path = f"{base}/{rel}"
            parent = os.path.dirname(remote_path).replace("\\", "/")
            ssh_manager.execute_command(f"mkdir -p '{parent}'", timeout=15)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            log(f"Загрузка {rel} на fallback-сервер...")
            ssh_manager.sftp.put(tmp_path, remote_path)
            os.unlink(tmp_path)
            try:
                ssh_manager.execute_command(
                    f"chown www-data:www-data '{remote_path}' 2>/dev/null || true",
                    timeout=15,
                )
            except Exception:
                pass
            status.synced.append(rel)
            status.missing.remove(item)
            status.content_stale = max(0, status.content_stale - 1)
            status.content_ok += 1
        except Exception as err:
            log(f"Ошибка зеркалирования {rel}: {err}")

    # Держим new/manifest.json = копия серверного моста (не GitHub).
    try:
        bridge = f"{base}/manifest.json"
        new_bridge = f"{base}/new/manifest.json"
        if _sftp_size(ssh_manager, bridge) is not None:
            ssh_manager.execute_command(f"mkdir -p '{base}/new'", timeout=15)
            ssh_manager.execute_command(f"cp -f '{bridge}' '{new_bridge}'", timeout=15)
            log("Скопирован серверный manifest.json -> new/manifest.json")
    except Exception as err:
        log(f"Не удалось обновить new/manifest.json: {err}")

    status.ok = not status.missing
    status.message = (
        f"Контент синхронизирован: {', '.join(status.synced) or 'без изменений'}"
        if status.ok
        else f"Не удалось зеркалировать контент: {len(status.missing)} файл(ов)"
    )
    log(status.message)
    return status


def sync_mirror(ssh_manager, remote_base_dir: str, progress_cb=None) -> MirrorStatus:
    def log(message: str):
        if progress_cb:
            progress_cb(message)

    status = check_mirror(ssh_manager, remote_base_dir)
    if status.ok or not status.missing:
        log(status.message)
        return status

    mirror_dir = f"{remote_base_dir.rstrip('/')}/{MIRROR_SUBPATH}"
    ssh_manager.execute_command(f"mkdir -p '{mirror_dir}'", timeout=15)

    for asset in list(status.missing):
        name = asset["name"]
        url = asset.get("browser_download_url", "")
        log(f"Скачивание {name} с GitHub...")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "NoteBuns-AdminPanel"})
            with urllib.request.urlopen(request, timeout=600) as response:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(response.read())
                    tmp_path = tmp.name
            log(f"Загрузка {name} на fallback-сервер...")
            ssh_manager.sftp.put(tmp_path, f"{mirror_dir}/{name}")
            os.unlink(tmp_path)
            status.synced.append(name)
            status.missing.remove(asset)
        except Exception as err:
            log(f"Ошибка зеркалирования {name}: {err}")

    status.ok = not status.missing
    status.message = (
        f"Exe-зеркало синхронизировано ({status.tag}): {', '.join(status.synced) or 'без изменений'}"
        if status.ok
        else f"Не удалось зеркалировать exe: {len(status.missing)} файла(ов)"
    )
    log(status.message)
    return status


def sync_all(ssh_manager, remote_base_dir: str, progress_cb=None) -> MirrorStatus:
    """Полная синхронизация: raw-контент + релизные ассеты."""
    def log(message: str):
        if progress_cb:
            progress_cb(message)

    content = sync_content_mirror(ssh_manager, remote_base_dir, progress_cb=progress_cb)
    assets = sync_mirror(ssh_manager, remote_base_dir, progress_cb=progress_cb)

    status = MirrorStatus(
        tag=assets.tag,
        ok=content.ok and assets.ok,
        content_ok=content.content_ok,
        content_stale=content.content_stale,
        assets_ok=assets.assets_ok,
        assets_stale=len(assets.missing),
        synced=list(content.synced) + list(assets.synced),
        missing=list(content.missing) + list(assets.missing),
    )
    status.message = f"{content.message} | {assets.message}"
    log(status.message)
    return status
