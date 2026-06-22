import urllib.request
import json
import os
import sys
import subprocess
import threading
from tkinter import messagebox
import customtkinter as ctk

CURRENT_VERSION = "1.3.7"
REPO_API = "https://api.github.com/repos/milkycloud-dev/admin-panel-minecraft/releases/latest"

def check_for_updates(app_window):
    """
    [RU] Проверяет наличие обновлений на GitHub в фоновом потоке.
    Запрашивает API релизов GitHub, сравнивает версии и при необходимости 
    предлагает пользователю обновиться.
    
    [EN] Checks for updates on GitHub in a background thread.
    Queries the GitHub releases API, compares versions, and prompts
    the user to update if necessary.
    """
    def t():
        try:
            # [RU] Отправка запроса к GitHub API / [EN] Send request to GitHub API
            req = urllib.request.Request(REPO_API, headers={"User-Agent": "NoteBuns-AdminPanel"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                
            # [RU] Получение последней версии из тега / [EN] Get latest version from tag
            latest_version = data.get("tag_name", "").lstrip("v")
            if not latest_version: return
            
            # [RU] Вспомогательная функция парсинга версии / [EN] Helper function to parse version
            def parse_ver(v):
                return [int(x) for x in v.split('.') if x.isdigit()]
            
            # [RU] Если новая версия больше текущей / [EN] If new version is greater than current
            if parse_ver(latest_version) > parse_ver(CURRENT_VERSION):
                assets = data.get("assets", [])
                if sys.platform == "win32":
                    target_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
                else:
                    target_asset = next((a for a in assets if "Linux" in a["name"]), None)
                    
                if target_asset:
                    # [RU] Вызываем окно обновления в главном потоке GUI / [EN] Call update prompt in main GUI thread
                    app_window.after(0, lambda: prompt_update(app_window, latest_version, target_asset["browser_download_url"]))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("Update check failed: Repository not found or private (404).")
            else:
                print(f"Update check failed: HTTP {e.code}")
        except Exception as e:
            print("Update check failed:", e)
    
    # [RU] Запуск потока / [EN] Start thread
    threading.Thread(target=t, daemon=True).start()

def prompt_update(app_window, version, url):
    """
    [RU] Показывает диалоговое окно с предложением обновить приложение.
    [EN] Shows a dialog prompt offering to update the application.
    """
    if messagebox.askyesno("Доступно обновление", f"Найдена новая версия {version} (текущая {CURRENT_VERSION}).\n\nПриложение будет загружено и перезапущено автоматически. Обновить сейчас?"):
        download_and_apply_update(app_window, url)

def download_and_apply_update(app_window, url):
    """
    [RU] Скачивает новый .exe файл, создает временный скрипт .bat 
    для замены текущего файла и перезапускает программу.
    
    [EN] Downloads the new .exe file, creates a temporary .bat script 
    to replace the current file, and restarts the program.
    """
    # [RU] Создаем окно с прогресс-баром / [EN] Create window with progress bar
    overlay = ctk.CTkToplevel(app_window)
    overlay.title("Обновление")
    overlay.geometry("400x150")
    overlay.attributes("-topmost", True)
    overlay.resizable(False, False)
    
    ctk.CTkLabel(overlay, text="Загрузка обновления...", font=("Inter", 16, "bold")).pack(pady=(20, 10))
    progress = ctk.CTkProgressBar(overlay, width=300)
    progress.pack()
    progress.set(0)
    
    def t():
        try:
            # [RU] Определяем пути файлов / [EN] Define file paths
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            new_exe_path = exe_path + ".new"
            
            # [RU] Загружаем файл частями и обновляем прогресс / [EN] Download file in chunks and update progress
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
                            overlay.after(0, progress.set, downloaded / total_size)
            
            # [RU] Создаем скрипт для обновления в зависимости от ОС / [EN] Create update script based on OS
            if sys.platform == "win32":
                bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
                with open(bat_path, "w") as f:
                    f.write(f'''@echo off
timeout /t 2 /nobreak > nul
del "{exe_path}"
move "{new_exe_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
''')
                subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                sh_path = os.path.join(os.path.dirname(exe_path), "update.sh")
                with open(sh_path, "w") as f:
                    f.write(f'''#!/bin/bash
sleep 2
rm "{exe_path}"
mv "{new_exe_path}" "{exe_path}"
chmod +x "{exe_path}"
"{exe_path}" &
rm "$0"
''')
                os.chmod(sh_path, 0o755)
                subprocess.Popen([sh_path], shell=True, start_new_session=True)
            
            overlay.after(0, app_window.destroy)
        except Exception as e:
            # [RU] Обработка ошибок загрузки / [EN] Handle download errors
            overlay.after(0, overlay.destroy)
            overlay.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось обновить: {e}"))
            
    # [RU] Запуск процесса обновления в потоке / [EN] Start update process in thread
    threading.Thread(target=t, daemon=True).start()
