import os
import json
import blake3

class ManifestManager:
    """
    [RU] Класс для работы с файлом манифеста Minecraft (manifest.json).
    Отвечает за генерацию хэшей, сбор списка локальных файлов и обновление манифеста.
    
    [EN] Class for working with the Minecraft manifest file (manifest.json).
    Responsible for generating hashes, collecting local file lists, and updating the manifest.
    """
    def __init__(self, config_manager):
        """
        [RU] Конструктор класса. Сохраняет ссылку на ConfigManager.
        [EN] Class constructor. Saves a reference to ConfigManager.
        """
        self.config = config_manager
        
    def get_paths(self):
        """
        [RU] Возвращает абсолютные пути к локальному файлу манифеста и папке с модами.
        [EN] Returns absolute paths to the local manifest file and mods directory.
        """
        local_manifest = self.config.get("paths", "local_manifest")
        mods_dir = self.config.get("paths", "local_mods_dir")
        # [RU] Определяем абсолютный путь относительно расположения этого скрипта
        # [EN] Resolve to absolute path relative to main.py
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, local_manifest), os.path.join(base_path, mods_dir)

    def ensure_dirs(self):
        """
        [RU] Проверяет существование папки с модами и создает её, если она отсутствует.
        [EN] Checks if the mods directory exists and creates it if it is missing.
        """
        _, mods_dir = self.get_paths()
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir)

    def get_local_mods(self):
        """
        [RU] Сканирует папку с модами и возвращает список всех файлов в ней.
        Игнорирует скрытые файлы (начинающиеся с точки).
        
        [EN] Scans the mods folder and returns a list of all files within it.
        Ignores hidden files (starting with a dot).
        """
        _, mods_dir = self.get_paths()
        mods = []
        if not os.path.exists(mods_dir):
            return mods, mods_dir
        for root, _, files in os.walk(mods_dir):
            for file in files:
                if not file.startswith('.'):
                    mods.append(os.path.join(root, file))
        return mods, mods_dir

    def compute_hash(self, filepath):
        """
        [RU] Вычисляет хэш-сумму файла по алгоритму BLAKE3 и определяет его размер.
        [EN] Computes the BLAKE3 hash sum of a file and determines its size.
        """
        h = blake3.blake3()
        size = 0
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
                size += len(chunk)
        return "b3:" + h.hexdigest(), size

    def update_manifest(self, mods_list, mods_dir):
        """
        [RU] Обновляет файл manifest.json. Удаляет старые записи модов и добавляет новые
        с вычисленными хэшами, размерами и URL-адресами для скачивания.
        
        [EN] Updates the manifest.json file. Removes old mod entries and adds new ones
        with computed hashes, sizes, and download URLs.
        """
        manifest_path, _ = self.get_paths()
        if not os.path.exists(manifest_path):
            raise Exception(f"Manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # [RU] Очищаем старые моды из манифеста / [EN] Clear old mods from manifest
        manifest['files'] = [f for f in manifest.get('files', []) if not f.get('path', '').startswith('mods/')]

        for local_path in mods_list:
            # [RU] Получаем относительный путь к файлу / [EN] Get relative file path
            rel_path = os.path.relpath(local_path, mods_dir).replace('\\', '/')
            # [RU] Формируем URL-адрес файла на сервере / [EN] Construct file URL on server
            url = f"https://download.example.com/mods/{rel_path}"
            
            # [RU] Вычисляем хэш и размер / [EN] Compute hash and size
            f_hash, f_size = self.compute_hash(local_path)
            
            # [RU] Добавляем информацию о файле в манифест / [EN] Add file info to manifest
            manifest['files'].append({
                "path": f"mods/{rel_path}",
                "url": url,
                "hash": f_hash,
                "size": f_size,
                "type": "file"
            })

        # [RU] Сохраняем обновленный манифест / [EN] Save updated manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
            
        return manifest_path
