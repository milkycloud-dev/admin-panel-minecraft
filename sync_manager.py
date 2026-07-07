import os
from ssh_manager import SSHManager

class SyncManager:
    """
    [RU] Менеджер синхронизации. Отвечает за сканирование локальных и удаленных
    директорий с модами для последующего сравнения и передачи.
    
    [EN] Synchronization Manager. Handles scanning of local and remote
    mod directories for subsequent comparison and transfer.
    """
    def __init__(self, config):
        """
        [RU] Конструктор. Принимает экземпляр ConfigManager.
        [EN] Constructor. Takes a ConfigManager instance.
        """
        self.config = config

    def get_remote_mods_dir(self, host_key):
        """
        Resolve remote mods directory for client or game server.
        Client download host stores jars under client/mods; game server uses mods/.
        """
        conf = self.config.get(host_key)
        base = (conf.get("remote_dir") or "").rstrip("/")
        subpath = conf.get("mods_subpath")
        if not subpath:
            subpath = "client/mods" if host_key == "client_server" else "mods"
        return f"{base}/{subpath}"

    def get_local_mods(self):
        """
        [RU] Сканирует локальную папку модов. Возвращает только файлы с расширением .jar.
        Возвращает кортеж (словарь_модов, полный_путь_к_папке).
        
        [EN] Scans the local mods directory. Returns only .jar files.
        Returns a tuple (mods_dictionary, full_folder_path).
        """
        mods_dir = self.config.get("paths", "local_mods_dir")
        # [RU] Получаем абсолютный путь / [EN] Get absolute path
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_mods_dir = os.path.join(base_path, mods_dir)
        
        # [RU] Если папки нет, создаем её / [EN] Create directory if it doesn't exist
        if not os.path.exists(full_mods_dir):
            os.makedirs(full_mods_dir)
            
        mods = {}
        for root, _, files in os.walk(full_mods_dir):
            for file in files:
                # [RU] Учитываем только .jar и игнорируем скрытые / [EN] Only consider .jar and ignore hidden
                if file.endswith('.jar') and not file.startswith('.'):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, full_mods_dir).replace('\\', '/')
                    size = os.path.getsize(abs_path)
                    mods[rel_path] = {"size": size, "abs_path": abs_path}
        return mods, full_mods_dir

    def get_remote_mods(self, host_key):
        """
        [RU] Подключается к удаленному серверу по SSH и сканирует папку модов.
        Использует Python-скрипт, передаваемый через base64, для быстрого сканирования.
        Возвращает кортеж (словарь_модов, сообщение_об_ошибке_если_есть).
        
        [EN] Connects to a remote server via SSH and scans the mods directory.
        Uses a base64-encoded Python script for fast scanning.
        Returns a tuple (mods_dictionary, error_message_if_any).
        """
        conf = self.config.get(host_key)
        if not conf.get("host"):
            return {}, ""
        ssh = SSHManager(conf["host"], conf["user"], conf["password"])
        ok, msg = ssh.connect()
        if not ok:
            return None, msg

        remote_mods_dir = self.get_remote_mods_dir(host_key)
        
        import base64
        # [RU] Скрипт, который будет выполнен на сервере / [EN] Script to be executed on the server
        script = f"""import os, hashlib
d = '{remote_mods_dir}'
if not os.path.exists(d):
    try: os.makedirs(d)
    except: pass
if os.path.exists(d):
    for r, _, files in os.walk(d):
        for f in files:
            if f.endswith('.jar') and not f.startswith('.'):
                p = os.path.join(r, f)
                try:
                    sz = os.path.getsize(p)
                    h = hashlib.md5()
                    with open(p, 'rb') as x:
                        while c := x.read(8192): h.update(c)
                    print(os.path.relpath(p, d).replace('\\\\', '/') + '|' + str(sz) + '|' + h.hexdigest())
                except Exception:
                    pass
"""
        # [RU] Кодируем скрипт в base64 для безопасной передачи / [EN] Encode script to base64 for safe transfer
        b64 = base64.b64encode(script.encode('utf-8')).decode('utf-8')
        py_cmd = (
            f"python3 -c \"import base64,sys;exec(base64.b64decode(sys.argv[1]).decode('utf-8'))\" {b64}"
            f" || python -c \"import base64,sys;exec(base64.b64decode(sys.argv[1]).decode('utf-8'))\" {b64}"
        )
        
        ok, out = ssh.execute_command(py_cmd, timeout=120)
        
        mods = {}
        if out and out.strip():
            # [RU] Парсим вывод скрипта / [EN] Parse script output
            for line in out.strip().split('\n'):
                parts = line.strip().split('|')
                if len(parts) >= 2:
                    rel_path = parts[0]
                    try:
                        size = int(parts[1])
                        checksum = parts[2] if len(parts) > 2 else ""
                        mods[rel_path] = {"size": size, "hash": checksum}
                    except ValueError:
                        pass

        ssh.disconnect()
        return mods, out if not ok else ""
