"""Local tests for index.json rebuild logic (launcher-compatible format)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from index_manifest_builder import (
    BASE_URL,
    compute_mod_entries,
    count_mod_entries,
    rebuild_index,
    rebuild_index_file,
)


def test_rebuild_preserves_archives_and_options():
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        (mods / "a.jar").write_bytes(b"jar-a")
        index = {
            "archives": {"libs.zip": {"url": "u", "hash": "b3:aa", "size": 1}},
            "files": {
                "options.txt": {"url": "u2", "hash": "b3:bb", "size": 2},
                "mods/old.jar": {"url": "u3", "hash": "b3:cc", "size": 3},
            },
        }
        out = rebuild_index(index, str(mods))
        assert "archives" in out and "libs.zip" in out["archives"]
        assert "options.txt" in out["files"]
        assert "mods/old.jar" not in out["files"]
        assert "mods/a.jar" in out["files"]
        assert out["files"]["mods/a.jar"]["hash"].startswith("b3:")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_add_and_remove_mod():
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        (mods / "one.jar").write_bytes(b"one")
        index = {"archives": {}, "files": {}}
        first = rebuild_index(json.loads(json.dumps(index)), str(mods))
        assert count_mod_entries(first) == 1

        (mods / "two.jar").write_bytes(b"two")
        second = rebuild_index(json.loads(json.dumps(first)), str(mods))
        assert count_mod_entries(second) == 2

        (mods / "one.jar").unlink()
        third = rebuild_index(json.loads(json.dumps(second)), str(mods))
        keys = [k for k in third["files"] if k.startswith("mods/")]
        assert keys == ["mods/two.jar"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_format_matches_launcher_file_entry():
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        payload = b"test-payload-123"
        (mods / "mod.jar").write_bytes(payload)
        index = rebuild_index({"archives": {}, "files": {}}, str(mods))
        entry = index["files"]["mods/mod.jar"]
        assert set(entry.keys()) == {"url", "hash", "size"}
        assert entry["url"] == f"{BASE_URL}/mods/mod.jar"
        assert entry["size"] == len(payload)
        assert entry["hash"].startswith("b3:")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rebuild_index_file_roundtrip():
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        (mods / "x.jar").write_bytes(b"x")
        index_path = tmp / "index.json"
        index_path.write_text(
            json.dumps({"archives": {"a.zip": {"url": "u", "hash": "b3:1", "size": 1}}, "files": {}}),
            encoding="utf-8",
        )
        out = rebuild_index_file(str(index_path), str(mods))
        assert count_mod_entries(out) == 1
        loaded = json.loads(index_path.read_text(encoding="utf-8"))
        assert loaded["files"]["mods/x.jar"]["hash"].startswith("b3:")
        assert "a.zip" in loaded["archives"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compute_mod_entries_skips_non_jar():
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        (mods / "a.jar").write_bytes(b"a")
        (mods / "readme.txt").write_bytes(b"no")
        (mods / ".hidden.jar").write_bytes(b"h")
        entries = compute_mod_entries(str(mods))
        assert list(entries.keys()) == ["mods/a.jar"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_rebuild_preserves_archives_and_options,
        test_add_and_remove_mod,
        test_format_matches_launcher_file_entry,
        test_rebuild_index_file_roundtrip,
        test_compute_mod_entries_skips_non_jar,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("PASS", fn.__name__)
        except Exception as err:
            failed += 1
            print("FAIL", fn.__name__, err)
    sys.exit(1 if failed else 0)
