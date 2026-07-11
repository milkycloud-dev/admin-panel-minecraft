import os
import time
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
        V2.1: client download host stores jars under cloud/mods; game server uses mods/.
        """
        conf = self.config.get(host_key)
        base = (conf.get("remote_dir") or "").rstrip("/")
        subpath = conf.get("mods_subpath")
        if not subpath:
            subpath = "cloud/mods" if host_key == "client_server" else "mods"
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

    def _scan_remote_mods_once(self, host_key):
        """
        Одна попытка: SSH connect + удалённый python-скан папки модов.
        Возвращает (mods_dict | None, error_str).
        None в mods = жёсткий сбой (сеть/SSH/команда); {} = папка пустая.
        """
        conf = self.config.get(host_key)
        if not conf.get("host"):
            return {}, ""

        host = conf["host"]
        label = conf.get("name") or host_key
        remote_mods_dir = self.get_remote_mods_dir(host_key)
        ssh = SSHManager(host, conf["user"], conf["password"])
        ok, msg = ssh.connect()
        if not ok:
            return None, (
                f"{label} ({host}): не удалось подключиться по SSH — {msg}"
            )

        import base64
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
        b64 = base64.b64encode(script.encode("utf-8")).decode("utf-8")
        py_cmd = (
            f"python3 -c \"import base64,sys;exec(base64.b64decode(sys.argv[1]).decode('utf-8'))\" {b64}"
            f" || python -c \"import base64,sys;exec(base64.b64decode(sys.argv[1]).decode('utf-8'))\" {b64}"
        )

        try:
            ok, out = ssh.execute_command(py_cmd, timeout=180)
        except Exception as exc:
            ssh.disconnect()
            return None, (
                f"{label} ({host}): сбой команды сканирования {remote_mods_dir} — {exc}"
            )

        if not ok and (not out or not out.strip()):
            ssh.disconnect()
            return None, (
                f"{label} ({host}): команда сканирования {remote_mods_dir} вернула ошибку "
                f"без вывода — {out or 'пустой stderr/stdout'}"
            )

        mods = {}
        if out and out.strip():
            for line in out.strip().split("\n"):
                parts = line.strip().split("|")
                if len(parts) >= 2:
                    rel_path = parts[0]
                    try:
                        size = int(parts[1])
                        checksum = parts[2] if len(parts) > 2 else ""
                        mods[rel_path] = {"size": size, "hash": checksum}
                    except ValueError:
                        pass

        ssh.disconnect()
        # Если команда упала, но строки jar всё же распарсились — считаем успехом.
        if not ok and not mods:
            return None, (
                f"{label} ({host}): не удалось прочитать моды в {remote_mods_dir} — "
                f"{(out or '').strip()[:300]}"
            )
        return mods, ""

    def get_remote_mods(self, host_key, max_attempts=3, retry_delay_sec=2, on_attempt=None):
        """
        Скан удалённых модов с повторами (по умолчанию до 3 попыток).
        on_attempt(attempt, max_attempts, err) — колбэк для лога промежуточных сбоев.
        При полном провале возвращает (None, подробная_ошибка).
        """
        conf = self.config.get(host_key)
        if not conf.get("host"):
            return {}, ""

        last_err = ""
        for attempt in range(1, max_attempts + 1):
            mods, err = self._scan_remote_mods_once(host_key)
            if not err:
                return mods if mods is not None else {}, ""
            last_err = err
            if on_attempt:
                on_attempt(attempt, max_attempts, err)
            if "Authentication failed" in err or "auth failed" in err.lower():
                return None, f"{err} (попытка {attempt}/{max_attempts}, повтор бессмысленен)"
            if attempt < max_attempts:
                time.sleep(retry_delay_sec)

        return None, (
            f"{last_err} | сканирование модов провалилось после {max_attempts} попыток"
        )
