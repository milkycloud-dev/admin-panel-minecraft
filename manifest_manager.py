import os
import json
import blake3

class ManifestManager:
    def __init__(self, config_manager):
        self.config = config_manager
        
    def get_paths(self):
        local_manifest = self.config.get("paths", "local_manifest")
        mods_dir = self.config.get("paths", "local_mods_dir")
        # Resolve to absolute path relative to main.py
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, local_manifest), os.path.join(base_path, mods_dir)

    def ensure_dirs(self):
        _, mods_dir = self.get_paths()
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir)

    def get_local_mods(self):
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
        h = blake3.blake3()
        size = 0
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
                size += len(chunk)
        return "b3:" + h.hexdigest(), size

    def update_manifest(self, mods_list, mods_dir):
        manifest_path, _ = self.get_paths()
        if not os.path.exists(manifest_path):
            raise Exception(f"Manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Clear old mods
        manifest['files'] = [f for f in manifest.get('files', []) if not f.get('path', '').startswith('mods/')]

        for local_path in mods_list:
            rel_path = os.path.relpath(local_path, mods_dir).replace('\\', '/')
            url = f"https://download.inflexus.world/mods/{rel_path}"
            
            f_hash, f_size = self.compute_hash(local_path)
            
            manifest['files'].append({
                "path": f"mods/{rel_path}",
                "url": url,
                "hash": f_hash,
                "size": f_size,
                "type": "file"
            })

        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
            
        return manifest_path
