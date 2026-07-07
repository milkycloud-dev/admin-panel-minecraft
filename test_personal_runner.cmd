@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PASS=0"
set "FAIL=0"
set "ROOT=%~dp0"
set "TEST_DIR=%TEMP%\mc-admin-personal-test"

echo.
echo === run_personal.cmd test harness ===
echo.

call :AssertEmbedTool "S1 embed_settings.py"
call :AssertBuildRunner "S2 build personal runner"
call :AssertDecodeJson "S3 base64 decodes to valid json"
call :AssertPersonalTest "S4 run_personal --test"
call :AssertSettingsDeployed "S5 settings file deployed"
call :AssertMainImports "S6 main.py imports"

echo.
echo ==============================
echo PASS: !PASS!  FAIL: !FAIL!
echo ==============================
if !FAIL! GTR 0 exit /b 1
exit /b 0

:AssertEmbedTool
python "%ROOT%tools\embed_settings.py" "%ROOT%admin_settings.json" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertBuildRunner
if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%" >nul 2>&1
mkdir "%TEST_DIR%" >nul 2>&1
python "%ROOT%tools\build_personal_runner.py" "%ROOT%admin_settings.json" "%TEST_DIR%\run_personal.cmd" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertDecodeJson
python -c "import base64,json,re; c=open(r'%TEST_DIR%\run_personal.cmd',encoding='utf-8').read(); m=re.search(r'SETTINGS_B64=([A-Za-z0-9+/=]+)',c); assert m; json.loads(base64.b64decode(m.group(1))); print('ok')" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] %~1
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertPersonalTest
set "MC_ADMIN_APP_DIR=%TEST_DIR%\app"
if exist "%MC_ADMIN_APP_DIR%" rmdir /s /q "%MC_ADMIN_APP_DIR%" >nul 2>&1
call "%TEST_DIR%\run_personal.cmd" --test >nul 2>&1
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    echo [FAIL] %~1 exit=!RC!
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
exit /b 0

:AssertSettingsDeployed
if not exist "%MC_ADMIN_APP_DIR%\admin_settings.json" (
    echo [FAIL] %~1 - file missing
    set /a FAIL+=1
    exit /b 0
)
python -c "import json; d=json.load(open(r'%MC_ADMIN_APP_DIR%\admin_settings.json',encoding='utf-8')); assert d.get('client_server',{}).get('host'); print('ok')" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] %~1 - invalid json
    set /a FAIL+=1
    exit /b 0
)
echo [PASS] %~1
set /a PASS+=1
rmdir /s /q "%TEST_DIR%" >nul 2>&1
exit /b 0

:AssertMainImports
pushd "%ROOT%"
python -c "import main; from ssh_manager import SSHManager; s=SSHManager('h','u','p'); assert hasattr(s,'download_file'); print('ok')" >nul 2>&1
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
