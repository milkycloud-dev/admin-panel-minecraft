"""Anti-fake + unit tests for remote mod scan retries."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_get_remote_mods_retries_three_times_then_returns_error():
    from sync_manager import SyncManager

    class Cfg:
        def get(self, section, key=None):
            data = {
                "client_server": {
                    "host": "127.0.0.1",
                    "user": "root",
                    "password": "x",
                    "remote_dir": "/var/www",
                    "mods_subpath": "cloud/mods",
                }
            }
            if key is None:
                return data[section]
            return data[section].get(key, "")

    sm = SyncManager(Cfg())
    calls = {"n": 0}

    class FlakySSH:
        def __init__(self, *a, **k):
            pass

        def connect(self):
            calls["n"] += 1
            return False, "Error reading SSH protocol banner"

        def disconnect(self):
            pass

        def execute_command(self, *a, **k):
            return False, "should not run"

    with patch("sync_manager.SSHManager", FlakySSH):
        with patch("sync_manager.time.sleep", lambda s: None):
            mods, err = sm.get_remote_mods("client_server", max_attempts=3)

    assert mods is None or mods == {}, mods
    assert err and "Error reading SSH protocol banner" in err, err
    assert "попытк" in err.lower() or "attempt" in err.lower() or "3/" in err or "после 3" in err.lower(), err
    assert calls["n"] == 3, f"expected 3 connect attempts, got {calls['n']}"


def test_get_remote_mods_succeeds_on_second_attempt():
    from sync_manager import SyncManager

    class Cfg:
        def get(self, section, key=None):
            data = {
                "client_server": {
                    "host": "127.0.0.1",
                    "user": "root",
                    "password": "x",
                    "remote_dir": "/var/www",
                    "mods_subpath": "cloud/mods",
                }
            }
            if key is None:
                return data[section]
            return data[section].get(key, "")

    sm = SyncManager(Cfg())
    state = {"n": 0}

    class RecoverSSH:
        def __init__(self, *a, **k):
            pass

        def connect(self):
            state["n"] += 1
            if state["n"] < 2:
                return False, "timed out"
            return True, "ok"

        def disconnect(self):
            pass

        def execute_command(self, *a, **k):
            return True, "demo.jar|12|abc"

    with patch("sync_manager.SSHManager", RecoverSSH):
        with patch("sync_manager.time.sleep", lambda s: None):
            mods, err = sm.get_remote_mods("client_server", max_attempts=3)

    assert not err, err
    assert "demo.jar" in mods
    assert state["n"] == 2


if __name__ == "__main__":
    failed = 0
    for fn in (
        test_get_remote_mods_retries_three_times_then_returns_error,
        test_get_remote_mods_succeeds_on_second_attempt,
    ):
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
