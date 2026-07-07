"""
Comprehensive launcher compatibility verification.

Simulates launcher flow:
  manifest.json -> index_urls[0] -> client/index.json -> sync mods/*

Validates admin-panel index_manifest_builder output matches launcher Rust structs.
"""
from __future__ import annotations

import json
import random
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import blake3

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from index_manifest_builder import BASE_URL, compute_mod_entries, rebuild_index

GITHUB_MANIFEST = (
    "https://raw.githubusercontent.com/milkycloud-dev/melody-launcher-minecraft/main/manifest.json"
)
SERVER_MANIFEST = "https://download.inflexus.world/manifest.json"
EXPECTED_INDEX_URL = "https://download.inflexus.world/client/index.json"

B3_RE = re.compile(r"^b3:[0-9a-f]{64}$", re.IGNORECASE)
REQUIRED_MANIFEST_KEYS = {
    "java_version",
    "java_windows",
    "java_linux",
    "minecraft_version",
    "index_urls",
    "files_base_url",
    "launcher_version",
}


class CheckResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed.append(msg)

    def fail(self, msg: str) -> None:
        self.failed.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def success(self) -> bool:
        return not self.failed


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AdminPanel-CompatCheck/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_hash_b3(path: Path, expected: str) -> bool:
    hasher = blake3.blake3()
    with path.open("rb") as handle:
        while chunk := handle.read(8192):
            hasher.update(chunk)
    return ("b3:" + hasher.hexdigest()).lower() == expected.strip().lower()


def check_manifest_source(result: CheckResult, label: str, manifest: dict) -> str | None:
    missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
    if missing:
        result.fail(f"{label}: missing keys {sorted(missing)}")
        return None

    index_urls = manifest.get("index_urls")
    if not isinstance(index_urls, list) or not index_urls:
        result.fail(f"{label}: index_urls empty or not a list")
        return None

    index_url = index_urls[0]
    if index_url != EXPECTED_INDEX_URL:
        result.warn(f"{label}: index_urls[0]={index_url!r} (expected {EXPECTED_INDEX_URL})")
    else:
        result.ok(f"{label}: index_urls[0] -> client/index.json")

    for platform in ("java_windows", "java_linux"):
        block = manifest.get(platform, {})
        if not block.get("urls") or not block.get("hash"):
            result.fail(f"{label}: {platform} missing urls/hash")
        elif not str(block["hash"]).startswith("b3:"):
            result.warn(f"{label}: {platform}.hash not b3: prefix (launcher supports it)")

    result.ok(f"{label}: manifest structure valid ({len(manifest)} top-level keys)")
    return index_url


def check_index_launcher_format(result: CheckResult, index: dict, label: str) -> None:
    if not isinstance(index, dict):
        result.fail(f"{label}: root is not object")
        return

    archives = index.get("archives")
    files = index.get("files")

    if archives is None:
        result.warn(f"{label}: archives missing (launcher uses #[serde(default)] -> OK)")
    elif not isinstance(archives, dict):
        result.fail(f"{label}: archives is not dict (launcher expects HashMap)")
        return

    if files is None:
        result.fail(f"{label}: files missing (launcher requires HashMap)")
        return
    if not isinstance(files, dict):
        result.fail(f"{label}: files is ARRAY not dict — launcher CANNOT parse (old bug)")
        return

    result.ok(f"{label}: index root is launcher-compatible (files=dict, archives=dict)")

    mod_keys = [k for k in files if str(k).startswith("mods/")]
    non_mod_keys = [k for k in files if not str(k).startswith("mods/")]
    result.ok(f"{label}: {len(mod_keys)} mod entries, {len(non_mod_keys)} non-mod files")

    bad_entries = []
    bad_urls = []
    bad_hashes = []
    bad_sizes = []

    for key, entry in files.items():
        if not isinstance(entry, dict):
            bad_entries.append(key)
            continue
        extra = set(entry.keys()) - {"url", "hash", "size"}
        if extra:
            bad_entries.append(f"{key}(extra:{extra})")
        for field in ("url", "hash", "size"):
            if field not in entry:
                bad_entries.append(f"{key}(no {field})")

        url = str(entry.get("url", ""))
        hash_val = str(entry.get("hash", ""))
        size = entry.get("size")

        if not B3_RE.match(hash_val) and not hash_val.startswith("b3:"):
            if str(key).startswith("mods/"):
                bad_hashes.append(key)
        elif str(key).startswith("mods/") and not B3_RE.match(hash_val):
            bad_hashes.append(key)

        if not isinstance(size, int) or size < 0:
            bad_sizes.append(key)

        norm_key = str(key).replace("\\", "/")
        if norm_key.startswith("mods/"):
            rel = norm_key[len("mods/") :]
            expected_url = f"{BASE_URL.rstrip('/')}/mods/{rel}"
            if url != expected_url:
                bad_urls.append((key, url, expected_url))

    if bad_entries:
        result.fail(f"{label}: malformed FileEntry: {bad_entries[:5]}")
    else:
        result.ok(f"{label}: all FileEntry objects have url/hash/size")

    if bad_hashes:
        result.fail(f"{label}: mod hashes not b3:<64hex>: {bad_hashes[:5]}")
    else:
        result.ok(f"{label}: all mod hashes are b3: format (launcher verify_hash)")

    if bad_sizes:
        result.fail(f"{label}: invalid size field: {bad_sizes[:5]}")
    else:
        result.ok(f"{label}: all size fields are integers")

    if bad_urls:
        result.fail(f"{label}: URL mismatch vs admin builder: {bad_urls[:3]}")
    else:
        result.ok(f"{label}: mod URLs match admin-panel pattern {BASE_URL}/mods/<rel>")

    for aname, aentry in (archives or {}).items():
        if not isinstance(aentry, dict):
            result.fail(f"{label}: archive {aname} not object")
            continue
        for field in ("url", "hash", "size"):
            if field not in aentry:
                result.fail(f"{label}: archive {aname} missing {field}")


def check_admin_builder_matches_server(result: CheckResult, index: dict) -> None:
    """SSH: compare live index mods with disk scan (same logic as admin rebuild)."""
    try:
        import base64

        from config_manager import ConfigManager
        from ssh_manager import SSHManager

        cm = ConfigManager()
        dc = cm.get("client_server")
        base = dc["remote_dir"]
        mods_dir = f"{base}/client/mods"

        scan_script = f"""import os, blake3
d={mods_dir!r}
for r,_,fs in os.walk(d):
  for f in fs:
    if f.endswith('.jar') and not f.startswith('.'):
      p=os.path.join(r,f)
      h=blake3.blake3(); sz=0
      with open(p,'rb') as x:
        while c:=x.read(8192): h.update(c); sz+=len(c)
      rl=os.path.relpath(p,d).replace(chr(92),'/')
      print('mods/'+rl+'|'+str(sz)+'|b3:'+h.hexdigest())
"""
        ssh = SSHManager(dc["host"], dc["user"], dc["password"], timeout=30)
        ok, msg = ssh.connect()
        if not ok:
            result.warn(f"SSH admin-match skipped: {msg}")
            return

        b64 = base64.b64encode(scan_script.encode()).decode()
        _, scan_out = ssh.execute_command(
            f'python3 -c "import base64,sys;exec(base64.b64decode(sys.argv[1]).decode())" {b64}',
            timeout=180,
        )
        ssh.disconnect()

        disk = {}
        for line in (scan_out or "").strip().splitlines():
            parts = line.strip().split("|")
            if len(parts) >= 3:
                disk[parts[0]] = {"size": int(parts[1]), "hash": parts[2]}

        index_mods = {
            k: v for k, v in index.get("files", {}).items() if str(k).startswith("mods/")
        }

        only_index = set(index_mods) - set(disk)
        only_disk = set(disk) - set(index_mods)
        mismatches = []
        for key in set(index_mods) & set(disk):
            ie, de = index_mods[key], disk[key]
            if ie.get("hash", "").lower() != de["hash"].lower():
                mismatches.append(key)
            if int(ie.get("size", 0)) != de["size"]:
                mismatches.append(f"{key}:size")

        if only_index:
            result.fail(f"SSH: stale index entries {len(only_index)}: {sorted(only_index)[:3]}")
        if only_disk:
            result.fail(f"SSH: missing from index {len(only_disk)}: {sorted(only_disk)[:3]}")
        if mismatches:
            result.fail(f"SSH: hash/size mismatches {len(mismatches)}: {mismatches[:3]}")
        if not only_index and not only_disk and not mismatches:
            result.ok(f"SSH: index matches disk scan ({len(disk)} mods) — admin rebuild would be identical")

        # Verify admin builder URL pattern for every mod on disk
        bad_urls = []
        for key in disk:
            rel = key[len("mods/") :]
            expected = f"{BASE_URL.rstrip('/')}/mods/{rel}"
            actual = index_mods.get(key, {}).get("url", "")
            if actual != expected:
                bad_urls.append(key)
        if bad_urls:
            result.fail(f"SSH: URL pattern mismatch for {bad_urls[:3]}")
        else:
            result.ok("SSH: all mod URLs match admin-panel builder pattern")

    except Exception as err:
        result.warn(f"SSH admin-match skipped: {err}")


def check_http_sample_hashes(result: CheckResult, index: dict, sample_size: int = 12) -> None:
    mod_items = [(k, v) for k, v in index.get("files", {}).items() if str(k).startswith("mods/")]
    if not mod_items:
        result.fail("HTTP sample: no mods in index")
        return

    random.seed(42)
    sample = random.sample(mod_items, min(sample_size, len(mod_items)))

    ok_count = 0
    for key, entry in sample:
        url = entry["url"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NoteBuns Launcher"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status != 200:
                    result.fail(f"HTTP {key}: status {resp.status}")
                    continue
                data = resp.read()
            if len(data) != entry["size"]:
                result.fail(f"HTTP {key}: size {len(data)} != index {entry['size']}")
                continue
            hasher = blake3.blake3()
            hasher.update(data)
            got = "b3:" + hasher.hexdigest()
            if got.lower() != str(entry["hash"]).lower():
                result.fail(f"HTTP {key}: hash mismatch")
                continue
            ok_count += 1
        except (urllib.error.URLError, TimeoutError) as err:
            result.fail(f"HTTP {key}: {err}")

    result.ok(f"HTTP sample: {ok_count}/{len(sample)} mods verified (download+hash+size)")


def check_manifest_not_used_for_mods(result: CheckResult, manifest: dict, label: str) -> None:
    files = manifest.get("files")
    if files is None:
        result.ok(f"{label}: manifest has no 'files' — correct (mods in index.json)")
    elif isinstance(files, list):
        mod_entries = [f for f in files if str(f.get("path", "")).startswith("mods/")]
        if mod_entries:
            result.fail(f"{label}: manifest still has {len(mod_entries)} mods in files[] array")
        else:
            result.ok(f"{label}: manifest files[] has no mods")
    elif isinstance(files, dict):
        mod_entries = [k for k in files if str(k).startswith("mods/")]
        if mod_entries:
            result.warn(f"{label}: manifest files dict has {len(mod_entries)} mods (unusual)")
        else:
            result.ok(f"{label}: manifest files dict has no mods")
    else:
        result.ok(f"{label}: manifest files field absent or empty")


def run_scenario(result: CheckResult, manifest_url: str, label: str) -> None:
    print(f"\n=== Scenario: {label} ===")
    try:
        manifest = fetch_json(manifest_url)
    except Exception as err:
        result.fail(f"{label}: cannot fetch manifest: {err}")
        return

    check_manifest_not_used_for_mods(result, manifest, label)
    index_url = check_manifest_source(result, label, manifest)
    if not index_url:
        return

    try:
        index = fetch_json(index_url)
    except Exception as err:
        result.fail(f"{label}: cannot fetch index from {index_url}: {err}")
        return

    check_index_launcher_format(result, index, label)

    if label.startswith("Server"):
        check_admin_builder_matches_server(result, index)
        check_http_sample_hashes(result, index)


def run_local_builder_scenarios(result: CheckResult) -> None:
    print("\n=== Scenario: Local admin builder ===")
    tmp = Path(tempfile.mkdtemp())
    try:
        mods = tmp / "mods"
        mods.mkdir()
        (mods / "alpha.jar").write_bytes(b"alpha-content")
        (mods / "sub" / "beta.jar").parent.mkdir(parents=True)
        (mods / "sub" / "beta.jar").write_bytes(b"beta-content")

        index = {
            "archives": {"libs.zip": {"url": "u", "hash": "b3:" + "a" * 64, "size": 1}},
            "files": {
                "options.txt": {"url": "u", "hash": "b3:" + "b" * 64, "size": 2},
                "mods/stale.jar": {"url": "u", "hash": "b3:" + "c" * 64, "size": 3},
            },
        }
        out = rebuild_index(json.loads(json.dumps(index)), str(mods))
        check_index_launcher_format(result, out, "local-builder-output")

        entries = compute_mod_entries(str(mods))
        for key, entry in entries.items():
            rel = key[len("mods/") :]
            path = mods / rel.replace("/", "\\") if "\\" in rel else mods / rel
            if not path.exists():
                path = mods / Path(rel)
            if path.exists() and not verify_hash_b3(path, entry["hash"]):
                result.fail(f"local builder hash wrong for {key}")
        result.ok("local builder: BLAKE3 hashes match disk files")
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    result = CheckResult()
    print("=" * 60)
    print("LAUNCHER <-> ADMIN PANEL COMPATIBILITY CHECK")
    print("=" * 60)

    run_scenario(result, GITHUB_MANIFEST, "GitHub manifest (launcher primary)")
    run_scenario(result, SERVER_MANIFEST, "Server manifest (launcher fallback)")
    run_local_builder_scenarios(result)

    print("\n" + "=" * 60)
    print(f"PASSED:  {len(result.passed)}")
    print(f"FAILED:  {len(result.failed)}")
    print(f"WARNINGS:{len(result.warnings)}")
    print("=" * 60)

    for item in result.passed:
        print(f"  [OK]   {item}")
    for item in result.warnings:
        print(f"  [WARN] {item}")
    for item in result.failed:
        print(f"  [FAIL] {item}")

    try:
        gh = fetch_json(GITHUB_MANIFEST)
        sv = fetch_json(SERVER_MANIFEST)
        if gh.get("index_urls", [None])[0] == sv.get("index_urls", [None])[0]:
            result.ok("GitHub and server manifest agree on index_urls[0]")
            print(f"  [OK]   GitHub and server manifest agree on index_urls[0]")
        else:
            result.fail(
                f"index_urls mismatch: GitHub={gh.get('index_urls')} server={sv.get('index_urls')}"
            )
            print("  [FAIL] index_urls mismatch")
    except Exception as err:
        result.fail(f"cross-manifest check: {err}")

    print("=" * 60)
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
