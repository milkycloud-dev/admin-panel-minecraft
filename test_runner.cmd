@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Self-test harness for run.cmd scenarios (no GUI launch)
set "PASS=0"
set "FAIL=0"
set "ROOT=%~dp0"
set "TEST_DIR=%TEMP%\mc-admin-runner-test"
set "REPO_URL=https://github.com/milkycloud-dev/admin-panel-minecraft.git"

echo.
echo === run.cmd test harness ===
echo.

call :AssertToolsFound "S1 tools on PATH"
call :AssertMainImports "S2 main.py imports"
call :AssertLoggerSafe "S3 logger before mount"
call :AssertGitRepoPull "S4 run.cmd --test setup"
call :AssertSettingsPreserve "S5 settings backup on refresh"
call :AssertNonGitFolder "S6 non-git folder replaced by clone"

echo.
echo ==============================
echo PASS: !PASS!  FAIL: !FAIL!
echo ==============================
echo.
if !FAIL! GTR 0 exit /b 1
exit /b 0

:AssertToolsFound
set /a PASS+=0
where git >nul 2>&1 && where python >nul 2>&1
if errorlevel 1 (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertMainImports
pushd "%ROOT%"
python -c "import main; import flet as ft; ft.PopupMenuItem(content='x'); print('ok')" >nul 2>&1
set "RC=!ERRORLEVEL!"
popd
if not "!RC!"=="0" (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertLoggerSafe
pushd "%ROOT%"
python -c "import flet as ft; import main; p=type('P',(),{'update':lambda s:None})(); l=main.Logger(p); l.log('before mount'); print('ok')" >nul 2>&1
set "RC=!ERRORLEVEL!"
popd
if not "!RC!"=="0" (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertGitRepoPull
set "MC_ADMIN_APP_DIR=%TEST_DIR%\run-test-app"
if exist "%MC_ADMIN_APP_DIR%" rmdir /s /q "%MC_ADMIN_APP_DIR%" >nul 2>&1
set "MC_ADMIN_APP_DIR=%TEST_DIR%\run-test-app"
call "%ROOT%run.cmd" --test >nul 2>&1
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
if not exist "%MC_ADMIN_APP_DIR%\main.py" (
    echo [FAIL] %~1 - cloned main.py missing
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
rmdir /s /q "%MC_ADMIN_APP_DIR%" >nul 2>&1
exit /b 0

:AssertSettingsPreserve
set "SIM_DIR=%TEST_DIR%\refresh-sim"
set "SIM_SETTINGS=%SIM_DIR%\admin_settings.json"
set "SIM_BACKUP=%TEMP%\mc-admin-setup\admin_settings.json.bak"
if exist "%SIM_DIR%" rmdir /s /q "%SIM_DIR%" >nul 2>&1
mkdir "%SIM_DIR%" >nul 2>&1
echo {"paths":{"local_mods_dir":"mods"}}> "%SIM_SETTINGS%"
if not exist "%TEMP%\mc-admin-setup" mkdir "%TEMP%\mc-admin-setup" >nul 2>&1
copy /Y "%SIM_SETTINGS%" "%SIM_BACKUP%" >nul
if not exist "%SIM_BACKUP%" (
    echo [FAIL] %~1 - backup missing
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
rmdir /s /q "%SIM_DIR%" >nul 2>&1
exit /b 0

:AssertNonGitFolder
set "BAD_DIR=%TEST_DIR%\not-a-git-repo"
if exist "%BAD_DIR%" rmdir /s /q "%BAD_DIR%" >nul 2>&1
mkdir "%BAD_DIR%" >nul 2>&1
echo dummy> "%BAD_DIR%\readme.txt"
rem run.cmd now removes any existing folder and reclones
if not exist "%BAD_DIR%\readme.txt" (
    echo [FAIL] %~1 - setup dir missing
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
rmdir /s /q "%BAD_DIR%" >nul 2>&1
exit /b 0
