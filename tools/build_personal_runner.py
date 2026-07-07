"""Build run_personal.cmd with embedded admin_settings.json (base64)."""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Personal launcher — embedded settings, fresh clone each run
set "REPO_URL=https://github.com/milkycloud-dev/admin-panel-minecraft.git"
if defined MC_ADMIN_APP_DIR (
    set "APP_DIR=%MC_ADMIN_APP_DIR%"
) else (
    set "APP_DIR=%USERPROFILE%\Desktop\admin-panel-minecraft"
)
set "SETUP_DIR=%TEMP%\mc-admin-setup"
set "SETTINGS_B64=__SETTINGS_B64__"

if not exist "%SETUP_DIR%" mkdir "%SETUP_DIR%" >nul 2>&1

echo.
echo ============================================
echo   Minecraft Admin Panel - Personal Run
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
call :WriteEmbeddedSettings
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

:WriteEmbeddedSettings
echo [SETUP] Writing embedded admin_settings.json...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$b='!SETTINGS_B64!';$p='%APP_DIR%\admin_settings.json';" ^
    "$j=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b));" ^
    "[IO.File]::WriteAllText($p,$j,[Text.UTF8Encoding]::new($false))"
if errorlevel 1 (
    echo ERROR: Failed to write embedded settings.
    exit /b 1
)
echo [OK] Settings deployed to %APP_DIR%\admin_settings.json
exit /b 0

:PrepareSource
echo [SETUP] Refreshing project from GitHub...
if exist "%APP_DIR%" (
    rmdir /s /q "%APP_DIR%" 2>nul
    if exist "%APP_DIR%" (
        echo ERROR: Could not remove "%APP_DIR%".
        exit /b 1
    )
)
"!GIT_CMD!" clone --branch main --depth 1 "%REPO_URL%" "%APP_DIR%"
if errorlevel 1 exit /b 1
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


def build(settings_path: Path, out_path: Path):
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    b64 = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8")
    ).decode("ascii")
    content = TEMPLATE.replace("__SETTINGS_B64__", b64)
    out_path.write_text(content, encoding="utf-8", newline="\r\n")
    print(f"Wrote {out_path} ({len(b64)} b64 chars)")


if __name__ == "__main__":
    settings = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "admin_settings.json"
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "run_personal.cmd"
    build(settings, output)
