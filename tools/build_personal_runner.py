"""
Сборка персональных раннеров для тиммейта (НЕ коммитить!):
  - run_personal.cmd  (Windows)
  - run_personal.sh   (Linux)

Вшивает:
  - admin_settings.json (SSH/хосты/пути);
  - manifest_sym.key + ed25519_private.key (+ public);
  - при каждом запуске: git fetch/reset к origin/main.

Usage:
  python tools/build_personal_runner.py
  python tools/build_personal_runner.py path/to/admin_settings.json [out_stem] [keys_dir]
  # out_stem without extension → writes out_stem.cmd and out_stem.sh
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEYS = ROOT.parent / "logs-agent" / "keys"

TEMPLATE_WIN = r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =============================================================================
rem PERSONAL TEAM RUNNER — contains secrets. Do NOT commit or publish.
rem Персональный раннер: настройки + ключи V2.1. НЕ коммитить / не публиковать.
rem =============================================================================
set "REPO_URL=https://github.com/milkycloud-dev/admin-panel-minecraft.git"
if defined MC_ADMIN_APP_DIR (
    set "APP_DIR=%MC_ADMIN_APP_DIR%"
) else (
    set "APP_DIR=%USERPROFILE%\Desktop\admin-panel-minecraft"
)
set "SETUP_DIR=%TEMP%\mc-admin-setup"
set "SETTINGS_B64=__SETTINGS_B64__"
set "SYM_KEY_B64=__SYM_KEY_B64__"
set "PRIV_KEY_B64=__PRIV_KEY_B64__"
set "PUB_KEY_B64=__PUB_KEY_B64__"

if not exist "%SETUP_DIR%" mkdir "%SETUP_DIR%" >nul 2>&1

echo.
echo ============================================
echo   Admin Panel V2.1 — Personal Team Run
echo ============================================
echo.

call :FindTools
if not defined GIT_CMD call :InstallGit
if not defined PYTHON_CMD call :InstallPython
call :FindTools
if not defined GIT_CMD goto :Fail
if not defined PYTHON_CMD goto :Fail

echo [OK] Git:    !GIT_CMD!
echo [OK] Python: !PYTHON_CMD!
echo [OK] App dir: %APP_DIR%
echo.

call :PrepareSource
if errorlevel 1 goto :Fail
call :WriteEmbeddedSecrets
if errorlevel 1 goto :Fail
call :InstallPythonPackages
if errorlevel 1 goto :Fail

if /I "%~1"=="--test" goto :TestDone

echo.
echo [RUN] Starting Minecraft Admin Panel...
pushd "%APP_DIR%"
"!PYTHON_CMD!" main.py
set "EXIT_CODE=!ERRORLEVEL!"
popd
if not "!EXIT_CODE!"=="0" (
    echo Application exited with code !EXIT_CODE!.
    pause
    exit /b !EXIT_CODE!
)
endlocal
exit /b 0

:TestDone
echo [TEST] Personal runner setup complete.
endlocal
exit /b 0

:WriteEmbeddedSecrets
echo [SETUP] Writing embedded settings + V2.1 keys...
if not exist "%APP_DIR%\keys" mkdir "%APP_DIR%\keys" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$k='%APP_DIR%\keys';" ^
  "[IO.File]::WriteAllText((Join-Path $k 'manifest_sym.key'), ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%SYM_KEY_B64%')).Trim()+[char]10));" ^
  "[IO.File]::WriteAllText((Join-Path $k 'ed25519_private.key'), ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%PRIV_KEY_B64%')).Trim()+[char]10));" ^
  "[IO.File]::WriteAllText((Join-Path $k 'ed25519_public.key'), ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%PUB_KEY_B64%')).Trim()+[char]10));" ^
  "$o=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%SETTINGS_B64%')) | ConvertFrom-Json;" ^
  "if (-not $o.PSObject.Properties['manifest_keys']) { $o | Add-Member manifest_keys ([pscustomobject]@{}) };" ^
  "$o.manifest_keys | Add-Member sym_key_file (Join-Path $k 'manifest_sym.key') -Force;" ^
  "$o.manifest_keys | Add-Member ed25519_private_file (Join-Path $k 'ed25519_private.key') -Force;" ^
  "if ($o.client_server) { $o.client_server | Add-Member mods_subpath 'cloud/mods' -Force };" ^
  "[IO.File]::WriteAllText((Join-Path '%APP_DIR%' 'admin_settings.json'), ($o | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))"
if errorlevel 1 (
    echo ERROR: Failed to write embedded secrets.
    exit /b 1
)
echo [OK] Settings and keys deployed to %APP_DIR%
exit /b 0

:PrepareSource
echo [SETUP] Ensuring latest code from GitHub (origin/main)...
if exist "%APP_DIR%\.git" (
    pushd "%APP_DIR%"
    "!GIT_CMD!" remote set-url origin "%REPO_URL%" >nul 2>&1
    "!GIT_CMD!" fetch --prune origin main
    if errorlevel 1 (
        echo [WARN] fetch failed, trying fresh clone...
        popd
        goto :FreshClone
    )
    for /f "delims=" %%A in ('"!GIT_CMD!" rev-parse HEAD') do set "LOCAL_SHA=%%A"
    for /f "delims=" %%A in ('"!GIT_CMD!" rev-parse origin/main') do set "REMOTE_SHA=%%A"
    echo [INFO] local=!LOCAL_SHA!
    echo [INFO] remote=!REMOTE_SHA!
    if /I not "!LOCAL_SHA!"=="!REMOTE_SHA!" (
        echo [SETUP] Updating to origin/main...
        "!GIT_CMD!" reset --hard origin/main
        if errorlevel 1 (popd & exit /b 1)
        "!GIT_CMD!" clean -fd
    ) else (
        echo [OK] Already up to date with GitHub main
    )
    popd
    exit /b 0
)

:FreshClone
if exist "%APP_DIR%" (
    rmdir /s /q "%APP_DIR%" 2>nul
    if exist "%APP_DIR%" (
        echo ERROR: Could not remove "%APP_DIR%". Close the panel and retry.
        exit /b 1
    )
)
"!GIT_CMD!" clone --branch main --depth 1 "%REPO_URL%" "%APP_DIR%"
if errorlevel 1 exit /b 1
echo [OK] Fresh clone from GitHub
exit /b 0

:InstallPythonPackages
echo [SETUP] Installing Python packages...
pushd "%APP_DIR%"
"!PYTHON_CMD!" -m pip install --upgrade pip -q
"!PYTHON_CMD!" -m pip install -r requirements.txt -q
if errorlevel 1 (popd & exit /b 1)
popd
exit /b 0

:FindTools
set "GIT_CMD="
set "PYTHON_CMD="
for /f "delims=" %%G in ('where git 2^>nul') do (set "GIT_CMD=%%G" & goto :FindTools_GitDone)
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles%\Git\cmd\git.exe"
:FindTools_GitDone
for /f "delims=" %%P in ('where python 2^>nul') do (set "PYTHON_CMD=%%P" & goto :FindTools_PyDone)
for %%V in (314 313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :FindTools_PyDone
    )
)
:FindTools_PyDone
exit /b 0

:InstallGit
where winget >nul 2>&1 && winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements --disable-interactivity
call :FindTools
if defined GIT_CMD exit /b 0
exit /b 1

:InstallPython
where winget >nul 2>&1 && winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --disable-interactivity
call :FindTools
if defined PYTHON_CMD exit /b 0
exit /b 1

:Fail
pause
exit /b 1
'''

TEMPLATE_SH = r'''#!/usr/bin/env bash
# =============================================================================
# PERSONAL TEAM RUNNER (Linux) — contains secrets. Do NOT commit or publish.
# Персональный раннер: настройки + ключи V2.1. НЕ коммитить / не публиковать.
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/milkycloud-dev/admin-panel-minecraft.git"
APP_DIR="${MC_ADMIN_APP_DIR:-$HOME/Desktop/admin-panel-minecraft}"
SETTINGS_B64="__SETTINGS_B64__"
SYM_KEY_B64="__SYM_KEY_B64__"
PRIV_KEY_B64="__PRIV_KEY_B64__"
PUB_KEY_B64="__PUB_KEY_B64__"

echo
echo "============================================"
echo "  Admin Panel V2.1 — Personal Team Run (Linux)"
echo "============================================"
echo

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: '$1' not found. Install it and retry."
    exit 1
  }
}

need_cmd git
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=python
else
  echo "ERROR: python3/python not found. Install Python 3.11+ and retry."
  exit 1
fi

echo "[OK] Git:    $(command -v git)"
echo "[OK] Python: $(command -v "$PYTHON_CMD")"
echo "[OK] App dir: $APP_DIR"
echo

prepare_source() {
  echo "[SETUP] Ensuring latest code from GitHub (origin/main)..."
  if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" remote set-url origin "$REPO_URL" >/dev/null 2>&1 || true
    if ! git -C "$APP_DIR" fetch --prune origin main; then
      echo "[WARN] fetch failed, trying fresh clone..."
      rm -rf "$APP_DIR"
    else
      LOCAL_SHA=$(git -C "$APP_DIR" rev-parse HEAD)
      REMOTE_SHA=$(git -C "$APP_DIR" rev-parse origin/main)
      echo "[INFO] local=$LOCAL_SHA"
      echo "[INFO] remote=$REMOTE_SHA"
      if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
        echo "[SETUP] Updating to origin/main..."
        git -C "$APP_DIR" reset --hard origin/main
        git -C "$APP_DIR" clean -fd
      else
        echo "[OK] Already up to date with GitHub main"
      fi
      return 0
    fi
  fi

  if [[ -e "$APP_DIR" ]]; then
    rm -rf "$APP_DIR"
  fi
  git clone --branch main --depth 1 "$REPO_URL" "$APP_DIR"
  echo "[OK] Fresh clone from GitHub"
}

write_embedded_secrets() {
  echo "[SETUP] Writing embedded settings + V2.1 keys..."
  mkdir -p "$APP_DIR/keys"
  APP_DIR="$APP_DIR" SETTINGS_B64="$SETTINGS_B64" \
  SYM_KEY_B64="$SYM_KEY_B64" PRIV_KEY_B64="$PRIV_KEY_B64" PUB_KEY_B64="$PUB_KEY_B64" \
  "$PYTHON_CMD" - <<'PY'
import base64, json, os
app = os.environ["APP_DIR"]
keys = os.path.join(app, "keys")
os.makedirs(keys, exist_ok=True)

def write_key(env_name, filename):
    raw = base64.b64decode(os.environ[env_name]).decode("utf-8").strip() + "\n"
    path = os.path.join(keys, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

write_key("SYM_KEY_B64", "manifest_sym.key")
write_key("PRIV_KEY_B64", "ed25519_private.key")
write_key("PUB_KEY_B64", "ed25519_public.key")

data = json.loads(base64.b64decode(os.environ["SETTINGS_B64"]).decode("utf-8"))
data.setdefault("manifest_keys", {})
data["manifest_keys"]["sym_key_file"] = os.path.join(keys, "manifest_sym.key")
data["manifest_keys"]["ed25519_private_file"] = os.path.join(keys, "ed25519_private.key")
if "client_server" in data:
    data["client_server"]["mods_subpath"] = "cloud/mods"
path = os.path.join(app, "admin_settings.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
    f.write("\n")
print("[OK] Settings and keys deployed to", app)
PY
}

install_python_packages() {
  echo "[SETUP] Installing Python packages..."
  "$PYTHON_CMD" -m pip install --upgrade pip -q
  "$PYTHON_CMD" -m pip install -r "$APP_DIR/requirements.txt" -q
}

prepare_source
write_embedded_secrets
install_python_packages

if [[ "${1:-}" == "--test" ]]; then
  echo "[TEST] Personal runner setup complete."
  exit 0
fi

echo
echo "[RUN] Starting Minecraft Admin Panel..."
cd "$APP_DIR"
exec "$PYTHON_CMD" main.py
'''


def _b64_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip().encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _b64_json(data: dict) -> str:
    return base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8")
    ).decode("ascii")


def _prepare_payload(settings_path: Path, keys_dir: Path) -> dict[str, str]:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings.setdefault("manifest_keys", {})
    settings["manifest_keys"]["sym_key_file"] = ""
    settings["manifest_keys"]["ed25519_private_file"] = ""
    if "client_server" in settings:
        settings["client_server"]["mods_subpath"] = "cloud/mods"

    sym = keys_dir / "manifest_sym.key"
    priv = keys_dir / "ed25519_private.key"
    pub = keys_dir / "ed25519_public.key"
    for p in (sym, priv, pub):
        if not p.is_file():
            raise FileNotFoundError(f"missing key file: {p}")

    return {
        "__SETTINGS_B64__": _b64_json(settings),
        "__SYM_KEY_B64__": _b64_file(sym),
        "__PRIV_KEY_B64__": _b64_file(priv),
        "__PUB_KEY_B64__": _b64_file(pub),
    }


def _fill(template: str, payload: dict[str, str]) -> str:
    content = template
    for key, value in payload.items():
        content = content.replace(key, value)
    return content


def build(settings_path: Path, out_path: Path, keys_dir: Path) -> None:
    """Build a single runner (.cmd or .sh) based on out_path suffix."""
    payload = _prepare_payload(settings_path, keys_dir)
    suffix = out_path.suffix.lower()
    if suffix == ".sh":
        content = _fill(TEMPLATE_SH, payload)
        newline = "\n"
    else:
        content = _fill(TEMPLATE_WIN, payload)
        newline = "\r\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8", newline=newline)
    if suffix == ".sh":
        try:
            out_path.chmod(out_path.stat().st_mode | 0o755)
        except OSError:
            pass
    print(f"Wrote {out_path}")
    print(f"  settings: {settings_path}")
    print(f"  keys:     {keys_dir}")
    print("  WARNING: file contains passwords + private Ed25519 — do NOT commit/push.")


def build_both(settings_path: Path, stem: Path, keys_dir: Path) -> tuple[Path, Path]:
    """Write stem.cmd and stem.sh next to each other."""
    win = stem.with_suffix(".cmd")
    sh = stem.with_suffix(".sh")
    build(settings_path, win, keys_dir)
    build(settings_path, sh, keys_dir)
    return win, sh


if __name__ == "__main__":
    settings = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "admin_settings.json"
    out_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "run_personal"
    keys = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_KEYS

    if out_arg.suffix.lower() in {".cmd", ".sh"}:
        build(settings, out_arg, keys)
    else:
        build_both(settings, out_arg, keys)
