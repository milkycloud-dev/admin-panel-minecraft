"""
Build client/index.json for NoteBuns launcher (IndexManifest format).

Launcher flow:
  manifest.json (root) -> metadata (java, index_urls)
  client/index.json    -> archives + files dict with mods/* entries (b3: hashes)
"""
import json
import os

import blake3

DEFAULT_BASE_URL = "https://download.inflexus.world/client"
BASE_URL = DEFAULT_BASE_URL


def compute_mod_entries(mods_dir: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    """Scan mods_dir and return launcher-compatible files dict entries."""
    base_url = base_url.rstrip("/")
    entries = {}
    if not os.path.isdir(mods_dir):
        return entries

    for root, _, files in os.walk(mods_dir):
        for name in files:
            if not name.endswith(".jar") or name.startswith("."):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, mods_dir).replace("\\", "/")
            key = f"mods/{rel}"
            hasher = blake3.blake3()
            size = 0
            with open(path, "rb") as handle:
                while chunk := handle.read(8192):
                    hasher.update(chunk)
                    size += len(chunk)
            entries[key] = {
                "url": f"{base_url}/mods/{rel}",
                "hash": "b3:" + hasher.hexdigest(),
                "size": size,
            }
    return entries


def rebuild_index(index: dict, mods_dir: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    """
    Rebuild mods/* section in index.json.
    Preserves archives and non-mods files (e.g. options.txt).
    """
    files = index.get("files", {})
    if not isinstance(files, dict):
        files = {}
    kept = {k: v for k, v in files.items() if not str(k).startswith("mods/")}
    kept.update(compute_mod_entries(mods_dir, base_url))
    index["files"] = kept
    if "archives" not in index:
        index["archives"] = {}
    return index


def rebuild_index_file(index_path: str, mods_dir: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    """Load index.json, rebuild mods, save, return updated data."""
    with open(index_path, "r", encoding="utf-8") as handle:
        index = json.load(handle)
    index = rebuild_index(index, mods_dir, base_url)
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return index


def remote_rebuild_script(index_path: str, mods_dir: str, base_url: str = DEFAULT_BASE_URL) -> str:
    """Python script executed on client server via SSH."""
    return f"""import os, json, blake3
index_path = {index_path!r}
mods_dir = {mods_dir!r}
base_url = {base_url!r}.rstrip('/')
with open(index_path, 'r', encoding='utf-8') as f:
    index = json.load(f)
files = index.get('files', {{}})
if not isinstance(files, dict):
    files = {{}}
kept = {{k: v for k, v in files.items() if not str(k).startswith('mods/')}}
for root, _, names in os.walk(mods_dir):
    for name in names:
        if not name.endswith('.jar') or name.startswith('.'):
            continue
        path = os.path.join(root, name)
        rel = os.path.relpath(path, mods_dir).replace(chr(92), '/')
        key = 'mods/' + rel
        h = blake3.blake3()
        sz = 0
        with open(path, 'rb') as x:
            while c := x.read(8192):
                h.update(c)
                sz += len(c)
        kept[key] = {{
            'url': base_url + '/mods/' + rel,
            'hash': 'b3:' + h.hexdigest(),
            'size': sz,
        }}
index['files'] = kept
if 'archives' not in index:
    index['archives'] = {{}}
with open(index_path, 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=2, ensure_ascii=False)
    f.write(chr(10))
mod_count = len([k for k in kept if k.startswith('mods/')])
print('OK mods=' + str(mod_count))
"""


def count_mod_entries(index: dict) -> int:
    files = index.get("files", {})
    if isinstance(files, dict):
        return len([k for k in files if str(k).startswith("mods/")])
    return 0
