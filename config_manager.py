import json
import os
import shutil
import tkinter.messagebox as messagebox
import customtkinter as ctk
import tkinter.filedialog as filedialog

class ConfigManager:
    """
    [RU] Управляет конфигурацией приложения (admin_settings.json).
    Отвечает за загрузку, сохранение и инициализацию настроек.
    
    [EN] Manages the application's configuration (admin_settings.json).
    Responsible for loading, saving, and initializing settings.
    """
    def __init__(self, config_path="admin_settings.json"):
        """
        [RU] Конструктор класса. Инициализирует путь к конфигурации.
        [EN] Class constructor. Initializes the configuration path.
        """
        self.config_path = config_path
        self._ensure_config()
        self.config = self._load()

    def _ensure_config(self):
        """
        [RU] Проверяет наличие файла настроек при запуске. Если файл отсутствует, 
        спрашивает пользователя: импортировать существующий или создать новый пустой.
        
        [EN] Ensures the config file exists on startup. If missing, 
        prompts user to import an existing one or create a new empty one.
        """
        if not os.path.exists(self.config_path):
            root = ctk.CTk()
            root.withdraw()
            
            answer = messagebox.askyesnocancel(
                "Настройки не найдены / Settings not found",
                f"Файл {self.config_path} не найден.\n\nНажмите 'Да', чтобы импортировать существующий файл.\nНажмите 'Нет', чтобы создать пустой шаблон."
            )
            
            if answer is True: # [RU] Пользователь выбрал импорт / [EN] User chose to import
                file_path = filedialog.askopenfilename(title="Выберите файл настроек (json)", filetypes=[("JSON", "*.json")])
                if file_path:
                    if os.path.abspath(file_path) != os.path.abspath(self.config_path):
                        shutil.copy(file_path, self.config_path)
                else:
                    self._create_empty()
            elif answer is False: # [RU] Пользователь выбрал создание пустого файла / [EN] User chose to create empty file
                self._create_empty()
            else: # [RU] Пользователь отменил действие, закрываем приложение / [EN] User canceled, close application
                import sys
                sys.exit(0)
            
            root.destroy()

    def _create_empty(self):
        """
        [RU] Создает пустой шаблон настроек по умолчанию (admin_settings.json).
        
        [EN] Creates a default empty configuration template (admin_settings.json).
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
        """
        [RU] Читает и загружает JSON файл в память.
        [EN] Reads and loads the JSON file into memory.
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self):
        """
        [RU] Сохраняет текущие изменения из памяти в JSON файл.
        [EN] Saves current changes from memory back to the JSON file.
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def get(self, section, key=None):
        """
        [RU] Возвращает значение по секции и ключу. Если ключ не указан, возвращает всю секцию.
        [EN] Returns the value by section and key. If key is not provided, returns the whole section.
        """
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key, "")

    def set(self, section, key, value):
        """
        [RU] Устанавливает новое значение для указанной секции и ключа, затем сохраняет файл.
        [EN] Sets a new value for the specified section and key, then saves the file.
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save()
