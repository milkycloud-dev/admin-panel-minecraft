import json
import os
import shutil
import tkinter.messagebox as messagebox
import customtkinter as ctk
import tkinter.filedialog as filedialog

class ConfigManager:
    """
    Manages the application's configuration (admin_settings.json).
    Управляет конфигурацией приложения.
    """
    def __init__(self, config_path="admin_settings.json"):
        self.config_path = config_path
        self._ensure_config()
        self.config = self._load()

    def _ensure_config(self):
        """
        Ensures the config file exists on startup. Prompts user if missing.
        Проверяет наличие файла настроек. Если нет - предлагает импорт или создание.
        """
        if not os.path.exists(self.config_path):
            root = ctk.CTk()
            root.withdraw()
            
            answer = messagebox.askyesnocancel(
                "Настройки не найдены / Settings not found",
                f"Файл {self.config_path} не найден.\n\nНажмите 'Да', чтобы импортировать существующий файл.\nНажмите 'Нет', чтобы создать пустой шаблон."
            )
            
            if answer is True: # Import
                file_path = filedialog.askopenfilename(title="Выберите файл настроек (json)", filetypes=[("JSON", "*.json")])
                if file_path:
                    shutil.copy(file_path, self.config_path)
                else:
                    self._create_empty()
            elif answer is False: # Create Empty
                self._create_empty()
            else: # Cancel / Close
                import sys
                sys.exit(0)
            
            root.destroy()

    def _create_empty(self):
        """
        Creates an empty configuration template.
        Создает пустой шаблон настроек.
        """
        empty_conf = {
            "client_server": {
                "name": "Клиент-сервер",
                "host": "",
                "user": "root",
                "password": "",
                "remote_dir": "/var/www/download.inflexus.world"
            },
            "game_server": {
                "name": "Игровой сервер",
                "host": "",
                "user": "root",
                "password": "",
                "remote_dir": "/root/mineroot/minecraft",
                "screen_name": "minecraft"
            },
            "paths": {
                "local_mods_dir": "mods"
            },
            "backups": {
                "excluded_folders": "bluemap, dynmap, coreprotect, logs, crash-reports, cache, backups",
                "7z_args": "-mx9 -mmt4"
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(empty_conf, f, indent=4)

    def _load(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def get(self, section, key=None):
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key, "")

    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save()
