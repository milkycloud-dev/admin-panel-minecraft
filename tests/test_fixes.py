"""Automated tests for bugfixes and sync paths."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Git-tracked files allowed to contain author emails (not server credentials).
_EMAIL_ALLOWLIST = {
    ".github/workflows/release.yml",
}

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_ALLOWED_IPS = {"127.0.0.1", "0.0.0.0"}
_PASSWORD_IN_JSON_RE = re.compile(r'"password"\s*:\s*"[^"]{2,}"', re.IGNORECASE)
_EMBEDDED_SETTINGS_RE = re.compile(r"SETTINGS_B64=[A-Za-z0-9+/=]{20,}")


def test_download_file_exists():
    from ssh_manager import SSHManager
    assert hasattr(SSHManager("h", "u", "p"), "download_file")


class _StubConfig:
    """Мини-конфиг без чтения admin_settings.json (герметичный тест)."""

    def __init__(self, data):
        self._data = data

    def get(self, section, key=None):
        if key is None:
            return self._data.get(section, {})
        return self._data.get(section, {}).get(key, "")


def test_client_mods_dir():
    from sync_manager import SyncManager
    # V2.1: у клиент-сервера моды лежат в cloud/mods
    sm = SyncManager(_StubConfig({"client_server": {"remote_dir": "/var/www/x", "mods_subpath": ""}}))
    path = sm.get_remote_mods_dir("client_server")
    assert path.endswith("cloud/mods"), path

    from config_manager import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["client_server"]["mods_subpath"] == "cloud/mods"


def test_game_mods_dir():
    from sync_manager import SyncManager
    sm = SyncManager(_StubConfig({"game_server": {"remote_dir": "/root/mc", "mods_subpath": ""}}))
    path = sm.get_remote_mods_dir("game_server")
    assert path.endswith("/mods") and "cloud" not in path, path


def test_updater_version():
    from updater import CURRENT_VERSION, _schedule_ui
    assert CURRENT_VERSION == "2.1.0"
    assert callable(_schedule_ui)


def test_schedule_ui_in_main():
    import main
    assert hasattr(main, "schedule_ui")


def test_build_personal_runner_script():
    script = ROOT / "tools" / "build_personal_runner.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "SETTINGS_B64" in text
    assert "admin_settings.json" in text


def _git_tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def test_no_secrets_in_tracked_sources():
    """Ensure no IPs, passwords, or embedded settings in git-tracked files."""
    binary_suffixes = {".png", ".ttf", ".ico", ".jpg", ".jpeg", ".gif", ".webp"}
    for rel in _git_tracked_files():
        path = ROOT / rel
        if not path.is_file() or path.suffix.lower() in binary_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")

        if rel not in _EMAIL_ALLOWLIST:
            for ip in _IPV4_RE.findall(text):
                assert ip in _ALLOWED_IPS, f"IP address {ip!r} found in tracked file {rel}"

        if _PASSWORD_IN_JSON_RE.search(text):
            assert False, f'non-empty JSON password value in tracked file {rel}'

        if _EMBEDDED_SETTINGS_RE.search(text) and "PASTE_OUTPUT" not in text:
            assert False, f"embedded SETTINGS_B64 payload in tracked file {rel}"


if __name__ == "__main__":
    tests = [
        test_download_file_exists,
        test_client_mods_dir,
        test_game_mods_dir,
        test_updater_version,
        test_schedule_ui_in_main,
        test_build_personal_runner_script,
        test_no_secrets_in_tracked_sources,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as err:
            failed += 1
            print(f"FAIL {fn.__name__}: {err}")
    sys.exit(1 if failed else 0)
