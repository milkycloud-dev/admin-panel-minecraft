"""
Сборка персонального run_personal.cmd для тиммейта (НЕ коммитить!).

Вшивает:
  - admin_settings.json (SSH/хосты/пути);
  - manifest_sym.key + ed25519_private.key (и public для полноты);
  - при каждом запуске: git fetch/reset к origin/main (актуальный код с GitHub).

Usage:
  python tools/build_personal_runner.py
  python tools/build_personal_runner.py path/to/admin_settings.json out.cmd path/to/keys_dir
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEYS = ROOT.parent / "logs-agent" / "keys"

TEMPLATE = r'''@echo off
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


def _b64_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip().encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _b64_json(data: dict) -> str:
    return base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8")
    ).decode("ascii")


def build(settings_path: Path, out_path: Path, keys_dir: Path) -> None:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    # Ensure V2.1 defaults in embedded settings (paths filled at runtime).
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

    content = (
        TEMPLATE.replace("__SETTINGS_B64__", _b64_json(settings))
        .replace("__SYM_KEY_B64__", _b64_file(sym))
        .replace("__PRIV_KEY_B64__", _b64_file(priv))
        .replace("__PUB_KEY_B64__", _b64_file(pub))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8", newline="\r\n")
    print(f"Wrote {out_path}")
    print(f"  settings: {settings_path}")
    print(f"  keys:     {keys_dir}")
    print("  WARNING: file contains passwords + private Ed25519 — do NOT commit/push.")


if __name__ == "__main__":
    settings = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "admin_settings.json"
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "run_personal.cmd"
    keys = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_KEYS
    build(settings, output, keys)
