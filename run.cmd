@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Minecraft Admin Panel — zero-install launcher
rem Clones to Desktop, installs missing tools/deps, runs main.py

set "REPO_URL=https://github.com/milkycloud-dev/admin-panel-minecraft.git"
if defined MC_ADMIN_APP_DIR (
    set "APP_DIR=%MC_ADMIN_APP_DIR%"
) else (
    set "APP_DIR=%USERPROFILE%\Desktop\admin-panel-minecraft"
)
set "SETUP_DIR=%TEMP%\mc-admin-setup"
set "PYTHON_CMD="
set "GIT_CMD="

if not exist "%SETUP_DIR%" mkdir "%SETUP_DIR%" >nul 2>&1

echo.
echo ============================================
echo   Minecraft Admin Panel - Setup and Run
echo ============================================
echo.

call :FindTools
if not defined GIT_CMD call :InstallGit
if not defined PYTHON_CMD call :InstallPython
call :FindTools

if not defined GIT_CMD (
    echo ERROR: Git is still unavailable after install attempt.
    goto :Fail
)
if not defined PYTHON_CMD (
    echo ERROR: Python is still unavailable after install attempt.
    goto :Fail
)

echo [OK] Git:    !GIT_CMD!
echo [OK] Python: !PYTHON_CMD!
echo [OK] App dir: %APP_DIR%
echo.

call :PrepareSource
if errorlevel 1 goto :Fail

call :InstallPythonPackages
if errorlevel 1 goto :Fail

rem Skip launch during automated self-test
if /I "%~1"=="--test" goto :TestDone

echo.
echo [RUN] Starting Minecraft Admin Panel...
pushd "%APP_DIR%"
"!PYTHON_CMD!" main.py
set "EXIT_CODE=!ERRORLEVEL!"
popd

if not "!EXIT_CODE!"=="0" (
    echo.
    echo Application exited with code !EXIT_CODE!.
    pause
    exit /b !EXIT_CODE!
)

endlocal
exit /b 0

:TestDone
echo [TEST] Setup complete. Skipping GUI launch.
endlocal
exit /b 0

:FindTools
set "GIT_CMD="
set "PYTHON_CMD="

for /f "delims=" %%G in ('where git 2^>nul') do (
    set "GIT_CMD=%%G"
    goto :FindTools_GitDone
)
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles%\Git\cmd\git.exe"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles(x86)%\Git\cmd\git.exe"
:FindTools_GitDone

for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_CMD=%%P"
    goto :FindTools_PyDone
)
for %%V in (314 313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :FindTools_PyDone
    )
)
if exist "%LOCALAPPDATA%\Programs\Python\Python3\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python3\python.exe"
)
:FindTools_PyDone
exit /b 0

:InstallGit
echo [SETUP] Git not found. Installing...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements --disable-interactivity
)
if not exist "%ProgramFiles%\Git\cmd\git.exe" (
    echo [SETUP] Downloading Git installer...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$u='https://github.com/git-for-windows/git/releases/download/v2.49.0.windows.1/Git-2.49.0-64-bit.exe';" ^
        "$o='%SETUP_DIR%\git-installer.exe';" ^
        "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
        "Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing;" ^
        "Start-Process -FilePath $o -ArgumentList '/VERYSILENT','/NORESTART','/NOCANCEL','/SP-' -Wait"
)
call :FindTools
if defined GIT_CMD exit /b 0
exit /b 1

:InstallPython
echo [SETUP] Python not found. Installing...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --disable-interactivity
)
call :FindTools
if defined PYTHON_CMD exit /b 0

echo [SETUP] Downloading Python installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$u='https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe';" ^
    "$o='%SETUP_DIR%\python-installer.exe';" ^
    "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing;" ^
    "Start-Process -FilePath $o -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_pip=1','Include_launcher=1' -Wait"
call :FindTools
if defined PYTHON_CMD exit /b 0
exit /b 1

:PrepareSource
echo [SETUP] Refreshing project from GitHub (settings preserved)...
set "SETTINGS_BACKUP=%SETUP_DIR%\admin_settings.json.bak"
if exist "%APP_DIR%\admin_settings.json" (
    copy /Y "%APP_DIR%\admin_settings.json" "%SETTINGS_BACKUP%" >nul
    echo [OK] Settings backed up.
) else (
    if exist "%SETTINGS_BACKUP%" del /f /q "%SETTINGS_BACKUP%" >nul 2>&1
)

if exist "%APP_DIR%" (
    echo [SETUP] Removing old copy...
    rmdir /s /q "%APP_DIR%" 2>nul
    if exist "%APP_DIR%" (
        echo ERROR: Could not remove "%APP_DIR%". Close the app and retry.
        exit /b 1
    )
)

echo [SETUP] Cloning latest main...
"!GIT_CMD!" clone --branch main --depth 1 "%REPO_URL%" "%APP_DIR%"
if errorlevel 1 (
    echo ERROR: git clone failed.
    exit /b 1
)

if exist "%SETTINGS_BACKUP%" (
    copy /Y "%SETTINGS_BACKUP%" "%APP_DIR%\admin_settings.json" >nul
    echo [OK] Settings restored.
)
exit /b 0

:InstallPythonPackages
echo [SETUP] Installing Python packages...
pushd "%APP_DIR%"
"!PYTHON_CMD!" -m pip install --upgrade pip
"!PYTHON_CMD!" -m pip install -r requirements.txt
if errorlevel 1 (
    popd
    exit /b 1
)
popd
exit /b 0

:Fail
echo.
pause
exit /b 1
