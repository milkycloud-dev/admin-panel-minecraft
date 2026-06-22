import os
from ssh_manager import SSHManager

class SyncManager:
    def __init__(self, config):
        self.config = config

    def get_local_mods(self):
        """Scan local mods directory — only .jar files."""
        mods_dir = self.config.get("paths", "local_mods_dir")
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_mods_dir = os.path.join(base_path, mods_dir)
        
        if not os.path.exists(full_mods_dir):
            os.makedirs(full_mods_dir)
            
        mods = {}
        for root, _, files in os.walk(full_mods_dir):
            for file in files:
                if file.endswith('.jar') and not file.startswith('.'):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, full_mods_dir).replace('\\', '/')
                    size = os.path.getsize(abs_path)
                    mods[rel_path] = {"size": size, "abs_path": abs_path}
        return mods, full_mods_dir

    def get_remote_mods(self, host_key):
        """Scan remote server mods directory via SSH — only .jar files."""
        conf = self.config.get(host_key)
        ssh = SSHManager(conf["host"], conf["user"], conf["password"])
        ok, msg = ssh.connect()
        if not ok:
            return None, msg

        remote_base = conf["remote_dir"]
        remote_mods_dir = f"{remote_base}/mods"
        
        import base64
        script = f"""import os
d = '{remote_mods_dir}'
if not os.path.exists(d):
    try: os.makedirs(d)
    except: pass
if os.path.exists(d):
    for r, _, files in os.walk(d):
        for f in files:
            if f.endswith('.jar') and not f.startswith('.'):
                p = os.path.join(r, f)
                print(os.path.relpath(p, d).replace('\\\\', '/') + '|' + str(os.path.getsize(p)))
"""
        b64 = base64.b64encode(script.encode('utf-8')).decode('utf-8')
        cmd = f"python3 -c \"import base64,sys;exec(base64.b64decode(sys.argv[1]).decode('utf-8'))\" {b64}"
        
        ok, out = ssh.execute_command(cmd)
        
        mods = {}
        if out and out.strip():
            for line in out.strip().split('\n'):
                parts = line.strip().split('|')
                if len(parts) == 2:
                    rel_path = parts[0]
                    try:
                        size = int(parts[1])
                        mods[rel_path] = {"size": size}
                    except ValueError:
                        pass

        ssh.disconnect()
        return mods, out if not ok else ""
