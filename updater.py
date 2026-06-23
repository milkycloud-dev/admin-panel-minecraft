import urllib.request
import json
import os
import sys
import subprocess
import threading
import flet as ft

CURRENT_VERSION = "2.0.2"
REPO_API = "https://api.github.com/repos/milkycloud-dev/admin-panel-minecraft/releases/latest"

def check_for_updates(page: ft.Page):
    """
    [RU] Проверяет наличие обновлений на GitHub в фоновом потоке.
    Запрашивает API релизов GitHub, сравнивает версии и при необходимости 
    предлагает пользователю обновиться.
    """
    def t():
        try:
            req = urllib.request.Request(REPO_API, headers={"User-Agent": "NoteBuns-AdminPanel"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                
            latest_version = data.get("tag_name", "").lstrip("v")
            if not latest_version: return
            
            def parse_ver(v):
                return [int(x) for x in v.split('.') if x.isdigit()]
            
            if parse_ver(latest_version) > parse_ver(CURRENT_VERSION):
                assets = data.get("assets", [])
                if sys.platform == "win32":
                    target_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
                else:
                    target_asset = next((a for a in assets if "Linux" in a["name"]), None)
                    
                if target_asset:
                    url = target_asset["browser_download_url"]
                    # Call update prompt safely in GUI thread
                    def safe_prompt():
                        prompt_update(page, latest_version, url)
                    page.run_task(lambda _: safe_prompt())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("Update check failed: Repository not found or private (404).")
            else:
                print(f"Update check failed: HTTP {e.code}")
        except Exception as e:
            print("Update check failed:", e)
    
    threading.Thread(target=t, daemon=True).start()

def prompt_update(page: ft.Page, version, url):
    def on_yes(e):
        dlg.open = False
        page.update()
        download_and_apply_update(page, url)
        
    def on_no(e):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Доступно обновление"),
        content=ft.Text(f"Найдена новая версия {version} (текущая {CURRENT_VERSION}).\nПриложение будет загружено и перезапущено автоматически.\nОбновить сейчас?"),
        actions=[
            ft.TextButton("Да", on_click=on_yes),
            ft.TextButton("Нет", on_click=on_no)
        ]
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def download_and_apply_update(page: ft.Page, url):
    progress = ft.ProgressBar(width=300, value=0)
    dlg = ft.AlertDialog(
        title=ft.Text("Обновление"),
        content=ft.Column([
            ft.Text("Загрузка обновления...", weight="bold"),
            progress
        ], tight=True),
        modal=True
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
    
    def t():
        try:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            new_exe_path = exe_path + ".new"
            
            with urllib.request.urlopen(url) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(new_exe_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk: break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress.value = downloaded / total_size
                            try: page.update()
                            except: pass
            
            if sys.platform == "win32":
                bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
                with open(bat_path, "w") as f:
                    f.write(f'''@echo off\ntimeout /t 2 /nobreak > nul\ndel "{exe_path}"\nmove "{new_exe_path}" "{exe_path}"\nstart "" "{exe_path}"\ndel "%~f0"\n''')
                subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                sh_path = os.path.join(os.path.dirname(exe_path), "update.sh")
                with open(sh_path, "w") as f:
                    f.write(f'''#!/bin/bash\nsleep 2\nrm "{exe_path}"\nmv "{new_exe_path}" "{exe_path}"\nchmod +x "{exe_path}"\n"{exe_path}" &\nrm "$0"\n''')
                os.chmod(sh_path, 0o755)
                subprocess.Popen([sh_path], shell=True, start_new_session=True)
            
            os._exit(0)
        except Exception as e:
            dlg.open = False
            err_dlg = ft.AlertDialog(title=ft.Text("Ошибка"), content=ft.Text(f"Не удалось обновить:\n{e}"))
            page.overlay.append(err_dlg)
            err_dlg.open = True
            try: page.update()
            except: pass
            
    threading.Thread(target=t, daemon=True).start()
