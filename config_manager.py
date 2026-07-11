import json
import os
import shutil
import sys

CONFIG_FILENAME = "admin_settings.json"

DEFAULT_CONFIG = {
    "client_server": {
        "name": "Клиент-сервер",
        "host": "",
        "user": "root",
        "password": "",
        "remote_dir": "/var/www/download.inflexus.world",
        # V2.1: файлы нового лаунчера живут в /cloud (mods, java, archives, manifest.json)
        # V2.1: the new launcher's files live in /cloud (mods, java, archives, manifest.json)
        "mods_subpath": "cloud/mods",
    },
    "game_server": {
        "name": "Игровой сервер",
        "host": "",
        "user": "root",
        "password": "",
        "remote_dir": "/root/mineroot/minecraft",
        "mods_subpath": "mods",
        "screen_name": "minecraft",
    },
    "paths": {
        "local_mods_dir": "mods",
    },
    # V2.1: ключи шифрования/подписи manifest (пути к файлам base64-ключей, НЕ сами ключи).
    # V2.1: manifest encryption/signing keys (paths to base64 key files, NOT the keys themselves).
    "manifest_keys": {
        "sym_key_file": "",
        "ed25519_private_file": "",
    },
    "backups": {
        "excluded_folders": "bluemap, dynmap, coreprotect, logs, crash-reports, cache, backups",
        "7z_args": "-mx9 -mmt4",
    },
}


def get_app_base_dir():
    """Directory of the exe (frozen) or project script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_config_search_dirs():
    """Fast fixed list of folders — no recursive scan."""
    home = os.path.expanduser("~")
    base = get_app_base_dir()
    candidates = [
        os.getcwd(),
        base,
        home,
        os.path.join(home, "Desktop"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Desktop", "admin-panel-minecraft"),
        os.path.join(home, "Downloads", "admin-panel-minecraft-main", "admin-panel-minecraft-main"),
    ]
    seen = set()
    result = []
    for path in candidates:
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen or not path:
            continue
        seen.add(norm)
        result.append(path)
    return result


def discover_config_file():
    """Return first valid admin_settings.json in known user folders."""
    for folder in get_config_search_dirs():
        if not os.path.isdir(folder):
            continue
        candidate = os.path.join(folder, CONFIG_FILENAME)
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and data:
                return candidate
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return None


class ConfigManager:
    """
    Manages admin_settings.json: auto-discovery, import/export, load/save.
    """

    def __init__(self, config_path=None):
        self.config_path = os.path.abspath(
            config_path or os.path.join(get_app_base_dir(), CONFIG_FILENAME)
        )
        self.import_required = False
        self.discovered_from = None
        self._ensure_config()
        self.config = self._load()

    def _ensure_config(self):
        if os.path.exists(self.config_path):
            return

        discovered = discover_config_file()
        if discovered:
            self.discovered_from = discovered
            if os.path.normcase(discovered) != os.path.normcase(self.config_path):
                shutil.copy2(discovered, self.config_path)
            return

        self.import_required = True
        self._create_empty()

    def _create_empty(self):
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(DEFAULT_CONFIG, handle, indent=4, ensure_ascii=False)

    def _load(self):
        with open(self.config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(self.config, handle, indent=4, ensure_ascii=False)

    def reload(self):
        self.config = self._load()
        return self.config

    def import_from(self, source_path):
        source_path = os.path.abspath(source_path)
        if os.path.normcase(source_path) != os.path.normcase(self.config_path):
            shutil.copy2(source_path, self.config_path)
        self.import_required = False
        self.discovered_from = source_path
        self.reload()

    def export_to(self, dest_path):
        dest_path = os.path.abspath(dest_path)
        self.save()
        if os.path.normcase(dest_path) != os.path.normcase(self.config_path):
            shutil.copy2(self.config_path, dest_path)

    def get(self, section, key=None):
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key, "")

    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save()
