import urllib.request
import json
import os
import sys
import subprocess
import threading
from tkinter import messagebox
import customtkinter as ctk

CURRENT_VERSION = "1.0.0"
REPO_API = "https://api.github.com/repos/milkycloud-dev/admin-panel-minecraft/releases/latest"

def check_for_updates(app_window):
    def t():
        try:
            req = urllib.request.Request(REPO_API, headers={"User-Agent": "NoteBuns-AdminPanel"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                
            latest_version = data.get("tag_name", "").lstrip("v")
            if not latest_version: return
            
            if latest_version != CURRENT_VERSION:
                assets = data.get("assets", [])
                exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
                if exe_asset:
                    app_window.after(0, lambda: prompt_update(app_window, latest_version, exe_asset["browser_download_url"]))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("Update check failed: Repository not found or private (404).")
            else:
                print(f"Update check failed: HTTP {e.code}")
        except Exception as e:
            print("Update check failed:", e)
    
    threading.Thread(target=t, daemon=True).start()

def prompt_update(app_window, version, url):
    if messagebox.askyesno("Доступно обновление", f"Найдена новая версия {version} (текущая {CURRENT_VERSION}).\n\nПриложение будет загружено и перезапущено автоматически. Обновить сейчас?"):
        download_and_apply_update(app_window, url)

def download_and_apply_update(app_window, url):
    # Create an overlay to show progress
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
                            overlay.after(0, progress.set, downloaded / total_size)
            
            # Apply update via batch script
            bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
            with open(bat_path, "w") as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak > nul
del "{exe_path}"
move "{new_exe_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
''')
            
            # Run batch script and exit
            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            overlay.after(0, app_window.destroy)
        except Exception as e:
            overlay.after(0, overlay.destroy)
            overlay.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось обновить: {e}"))
            
    threading.Thread(target=t, daemon=True).start()
