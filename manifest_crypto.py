"""
Криптография единого manifest для лаунчера NoteBuns V2.1.

Схема (вариант C): содержимое manifest шифруется симметрично (AES-256-GCM),
затем шифртекст подписывается Ed25519. Лаунчер проверяет подпись публичным
ключом и расшифровывает симметричным ключом (оба вшиты в бинарник обфусцированно).

Формат конверта, который кладём в /cloud/manifest.json:
    {
      "v": 1,
      "alg": "aesgcm+ed25519",
      "sig": "<base64 ed25519(raw)>",
      "payload": "<base64 raw>"
    }
где raw = nonce(12 байт) + ciphertext(с GCM-тегом). Подпись считается по raw.

Все ключи хранятся в base64. Совместимо с Rust-крейтами aes-gcm и ed25519-dalek.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization

ENVELOPE_VERSION = 1
ENVELOPE_ALG = "aesgcm+ed25519"
NONCE_LEN = 12  # стандартный размер nonce для AES-GCM


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.strip())


def generate_keys() -> dict[str, str]:
    """Сгенерировать новый комплект ключей (base64). Возвращает dict с тремя ключами."""
    sym = os.urandom(32)  # AES-256
    priv = Ed25519PrivateKey.generate()
    priv_raw = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "sym_key": _b64e(sym),
        "ed25519_private": _b64e(priv_raw),
        "ed25519_public": _b64e(pub_raw),
    }


def seal_manifest(manifest: dict[str, Any], sym_key_b64: str, ed_priv_b64: str) -> dict[str, str]:
    """Зашифровать и подписать manifest, вернуть конверт (dict, готовый к json.dump)."""
    plaintext = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    sym_key = _b64d(sym_key_b64)
    if len(sym_key) != 32:
        raise ValueError("MANIFEST_SYM_KEY должен быть 32 байта (AES-256) в base64")

    nonce = os.urandom(NONCE_LEN)
    ciphertext = AESGCM(sym_key).encrypt(nonce, plaintext, None)  # тег добавляется в конец
    raw = nonce + ciphertext

    priv = Ed25519PrivateKey.from_private_bytes(_b64d(ed_priv_b64))
    signature = priv.sign(raw)

    return {
        "v": ENVELOPE_VERSION,
        "alg": ENVELOPE_ALG,
        "sig": _b64e(signature),
        "payload": _b64e(raw),
    }


def open_manifest(envelope: dict[str, Any], sym_key_b64: str, ed_pub_b64: str) -> dict[str, Any]:
    """Проверить подпись и расшифровать конверт (используется в тестах и для самопроверки)."""
    raw = _b64d(envelope["payload"])
    sig = _b64d(envelope["sig"])

    pub = Ed25519PublicKey.from_public_bytes(_b64d(ed_pub_b64))
    pub.verify(sig, raw)  # бросит исключение при неверной подписи

    nonce, ciphertext = raw[:NONCE_LEN], raw[NONCE_LEN:]
    plaintext = AESGCM(_b64d(sym_key_b64)).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manifest crypto helper")
    parser.add_argument("cmd", choices=["gen", "seal", "open"], help="действие")
    parser.add_argument("--in", dest="inp", help="входной JSON-файл")
    parser.add_argument("--out", dest="out", help="выходной файл")
    parser.add_argument("--sym", help="base64 симметричного ключа")
    parser.add_argument("--priv", help="base64 приватного Ed25519")
    parser.add_argument("--pub", help="base64 публичного Ed25519")
    args = parser.parse_args()

    if args.cmd == "gen":
        print(json.dumps(generate_keys(), indent=2))
    elif args.cmd == "seal":
        manifest = json.load(open(args.inp, encoding="utf-8"))
        env = seal_manifest(manifest, args.sym, args.priv)
        out = json.dumps(env, indent=1)
        (open(args.out, "w", encoding="utf-8").write(out) if args.out else print(out))
    elif args.cmd == "open":
        env = json.load(open(args.inp, encoding="utf-8"))
        print(json.dumps(open_manifest(env, args.sym, args.pub), indent=2, ensure_ascii=False))
