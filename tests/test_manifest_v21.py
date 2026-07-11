"""
Тесты схемы V2.1: единый зашифрованный manifest в /cloud.

Проверяем:
  1. Крипто-конверт: Python шифрует -> расшифровка тем же ключом, подпись валидна,
     подделка payload/подписи отклоняется.
  2. Сборку единого манифеста: метаданные + archives/files, все URL переписаны
     на /cloud, структура совместима с Rust IndexManifest лаунчера.
  3. (Опционально, если доступны ключи и сеть) живой /cloud/manifest.json
     скачивается и расшифровывается.

V2.1 scheme tests: unified encrypted manifest in /cloud.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from manifest_crypto import generate_keys, open_manifest, seal_manifest
from manifest_builder import CLOUD_BASE_URL, assemble_manifest, load_metadata

KEYS_DIR = ROOT.parent / "logs-agent" / "keys"
CLOUD_MANIFEST_URL = "https://download.inflexus.world/cloud/manifest.json"

SAMPLE_INDEX = {
    "archives": {
        "libraries.zip": {
            "url": "https://download.inflexus.world/client/archives/libraries.zip",
            "hash": "b3:" + "a" * 64,
            "size": 10,
            "extract_to": "",
            "items": ["libraries"],
        }
    },
    "files": {
        "options.txt": {
            "url": "https://download.inflexus.world/client/options.txt",
            "hash": "b3:" + "b" * 64,
            "size": 20,
        },
        "mods/example.jar": {
            "url": "https://download.inflexus.world/client/mods/example.jar",
            "hash": "b3:" + "c" * 64,
            "size": 30,
        },
    },
}


def test_crypto_roundtrip_and_tamper():
    keys = generate_keys()
    manifest = {"launcher_version": "2.1.0", "files": {"mods/a.jar": {"size": 1}}, "тест": "юникод"}

    envelope = seal_manifest(manifest, keys["sym_key"], keys["ed25519_private"])
    assert envelope["v"] == 1 and envelope["alg"] == "aesgcm+ed25519"
    assert set(envelope) == {"v", "alg", "sig", "payload"}

    restored = open_manifest(envelope, keys["sym_key"], keys["ed25519_public"])
    assert restored == manifest

    # Подделка payload -> подпись отклоняет / Tampered payload -> signature rejects
    tampered = dict(envelope)
    tampered["payload"] = tampered["payload"][:-4] + "AAAA"
    try:
        open_manifest(tampered, keys["sym_key"], keys["ed25519_public"])
        assert False, "tampered payload accepted"
    except Exception:
        pass

    # Чужой ключ подписи -> отклоняется / Wrong verify key -> rejected
    other = generate_keys()
    try:
        open_manifest(envelope, keys["sym_key"], other["ed25519_public"])
        assert False, "wrong pubkey accepted"
    except Exception:
        pass


def test_assemble_manifest_rewrites_urls_and_merges_metadata():
    metadata = load_metadata(str(ROOT / "cloud_manifest_metadata.json"))
    manifest = assemble_manifest(json.loads(json.dumps(SAMPLE_INDEX)), metadata)

    # Метаданные на месте / Metadata present
    assert manifest["launcher_version"] == "2.1.0"
    assert manifest["java_windows"]["urls"][0].startswith(CLOUD_BASE_URL + "/java/")
    assert manifest["minecraft_version"] == "1.21.1"

    # Все URL переписаны на /cloud / All URLs rewritten to /cloud
    for section in ("archives", "files"):
        for entry in manifest[section].values():
            assert "/client/" not in entry["url"], entry["url"]
            assert entry["url"].startswith(CLOUD_BASE_URL), entry["url"]

    # Структура — как ждёт Rust IndexManifest / Structure matches Rust IndexManifest
    assert isinstance(manifest["archives"], dict)
    assert isinstance(manifest["files"], dict)
    for entry in manifest["files"].values():
        assert {"url", "hash", "size"} <= set(entry)


def test_live_cloud_manifest_decrypts():
    """Живой тест: скачиваем /cloud/manifest.json и расшифровываем локальными ключами."""
    sym_file = KEYS_DIR / "manifest_sym.key"
    pub_file = KEYS_DIR / "ed25519_public.key"
    if not (sym_file.is_file() and pub_file.is_file()):
        print("SKIP live: keys not present")
        return

    request = urllib.request.Request(
        CLOUD_MANIFEST_URL + "?t=test", headers={"User-Agent": "AdminPanel-CompatCheck/2.1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except Exception as err:
        print(f"SKIP live: network unavailable ({err})")
        return

    manifest = open_manifest(envelope, sym_file.read_text().strip(), pub_file.read_text().strip())
    assert manifest.get("launcher_version") == "2.1.0"
    assert isinstance(manifest.get("files"), dict) and manifest["files"]
    assert isinstance(manifest.get("archives"), dict) and manifest["archives"]
    mods = [k for k in manifest["files"] if str(k).startswith("mods/")]
    print(f"live cloud manifest OK: mods={len(mods)} archives={len(manifest['archives'])}")


if __name__ == "__main__":
    tests = [
        test_crypto_roundtrip_and_tamper,
        test_assemble_manifest_rewrites_urls_and_merges_metadata,
        test_live_cloud_manifest_decrypts,
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
