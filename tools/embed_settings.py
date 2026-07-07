"""Embed admin_settings.json as base64 for run_personal.cmd."""
import base64
import json
import sys
from pathlib import Path


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "admin_settings.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8")
    print(base64.b64encode(payload).decode("ascii"))


if __name__ == "__main__":
    main()
