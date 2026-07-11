"""
Сборка единого зашифрованного manifest.json для лаунчера NoteBuns V2.1.

В V2.1 нет отдельного index.json: и метаданные (Java, версии, обновления),
и списки файлов/архивов лежат в ОДНОМ файле /cloud/manifest.json, который
зашифрован (AES-256-GCM) и подписан (Ed25519) через manifest_crypto.

Здесь мы собираем итоговый (открытый) словарь манифеста:
    metadata (java/версии/fallbacks/launcher_version) + {archives, files}
затем «запечатываем» его и записываем зашифрованный конверт.

Building the unified encrypted manifest.json for the NoteBuns V2.1 launcher.
In V2.1 there is no separate index.json: metadata and file/archive listings live
in a SINGLE encrypted+signed /cloud/manifest.json file.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from index_manifest_builder import compute_mod_entries, load_index
from manifest_crypto import seal_manifest

# База для ссылок нового клиента (папка /cloud на сервере).
# Base URL for the new client's links (the /cloud folder on the server).
CLOUD_BASE_URL = "https://download.inflexus.world/cloud"

# Старая база (использовалась в client/index.json) — для переноса ссылок.
# Old base (used in client/index.json) — for rewriting links.
LEGACY_BASE_URL = "https://download.inflexus.world/client"


def load_metadata(path: str) -> dict[str, Any]:
    """Загрузить метаданные манифеста (java, версии, fallbacks, launcher_version)."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Файл метаданных должен быть JSON-объектом")
    return data


def rewrite_urls(section: dict[str, Any], old_base: str, new_base: str) -> dict[str, Any]:
    """Переписать все url c old_base на new_base в разделе archives/files."""
    out: dict[str, Any] = {}
    for key, entry in section.items():
        entry = dict(entry)
        url = entry.get("url", "")
        if isinstance(url, str) and url.startswith(old_base):
            entry["url"] = new_base.rstrip("/") + url[len(old_base):]
        out[key] = entry
    return out


def assemble_manifest(
    index: dict[str, Any],
    metadata: dict[str, Any],
    old_base: str = LEGACY_BASE_URL,
    new_base: str = CLOUD_BASE_URL,
) -> dict[str, Any]:
    """
    Собрать единый манифест: метаданные + архивы + файлы.
    Ссылки внутри archives/files переносятся с old_base на new_base.
    """
    manifest = copy.deepcopy(metadata)
    archives = index.get("archives", {}) if isinstance(index.get("archives"), dict) else {}
    files = index.get("files", {}) if isinstance(index.get("files"), dict) else {}
    manifest["archives"] = rewrite_urls(archives, old_base, new_base)
    manifest["files"] = rewrite_urls(files, old_base, new_base)
    return manifest


def build_from_existing_index(
    index_path: str,
    metadata_path: str,
    old_base: str = LEGACY_BASE_URL,
    new_base: str = CLOUD_BASE_URL,
) -> dict[str, Any]:
    """Собрать открытый манифест из существующего index.json + метаданных."""
    index = load_index(index_path)
    metadata = load_metadata(metadata_path)
    return assemble_manifest(index, metadata, old_base, new_base)


def build_from_mods_dir(
    mods_dir: str,
    metadata_path: str,
    existing_index_path: str | None = None,
    new_base: str = CLOUD_BASE_URL,
) -> dict[str, Any]:
    """
    Собрать открытый манифест, пересканировав папку mods (blake3).
    Архивы и не-mods файлы берутся из existing_index_path (если задан), иначе пусто.
    """
    metadata = load_metadata(metadata_path)
    index = load_index(existing_index_path) if existing_index_path else {"archives": {}, "files": {}}

    archives = index.get("archives", {}) if isinstance(index.get("archives"), dict) else {}
    files = index.get("files", {}) if isinstance(index.get("files"), dict) else {}
    # Сохраняем не-mods файлы (например, options.txt) и пересобираем mods/*.
    kept = {k: v for k, v in files.items() if not str(k).startswith("mods/")}
    kept.update(compute_mod_entries(mods_dir, new_base))

    manifest = copy.deepcopy(metadata)
    manifest["archives"] = rewrite_urls(archives, LEGACY_BASE_URL, new_base)
    manifest["files"] = rewrite_urls(kept, LEGACY_BASE_URL, new_base)
    return manifest


def seal_and_write(manifest: dict[str, Any], out_path: str, sym_key_b64: str, ed_priv_b64: str) -> dict[str, Any]:
    """Зашифровать+подписать манифест и записать конверт в out_path. Вернуть конверт."""
    envelope = seal_manifest(manifest, sym_key_b64, ed_priv_b64)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(envelope, handle, indent=1)
        handle.write("\n")
    return envelope


def _read_key(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Сборка зашифрованного manifest.json V2.1")
    parser.add_argument("--index", help="путь к существующему index.json (архивы+файлы)")
    parser.add_argument("--mods", help="папка mods для пересканирования (blake3)")
    parser.add_argument("--metadata", default="cloud_manifest_metadata.json", help="файл метаданных")
    parser.add_argument("--out", required=True, help="куда записать зашифрованный manifest.json")
    parser.add_argument("--sym-key-file", required=True, help="файл с base64 симметричного ключа")
    parser.add_argument("--priv-key-file", required=True, help="файл с base64 приватного Ed25519")
    parser.add_argument("--plain-out", help="(опц.) записать открытый манифест для проверки")
    args = parser.parse_args()

    if args.mods:
        manifest = build_from_mods_dir(args.mods, args.metadata, args.index)
    elif args.index:
        manifest = build_from_existing_index(args.index, args.metadata)
    else:
        parser.error("нужно указать --index и/или --mods")

    if args.plain_out:
        with open(args.plain_out, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    sym = _read_key(args.sym_key_file)
    priv = _read_key(args.priv_key_file)
    seal_and_write(manifest, args.out, sym, priv)

    n_arch = len(manifest.get("archives", {}))
    n_files = len(manifest.get("files", {}))
    print(f"OK archives={n_arch} files={n_files} -> {args.out}")
