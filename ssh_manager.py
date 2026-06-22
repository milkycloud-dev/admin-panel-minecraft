import paramiko
import os

class SSHManager:
    def __init__(self, host, user, password, timeout=5):
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.ssh = None
        self.sftp = None

    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host, username=self.user, password=self.password, timeout=self.timeout)
            self.sftp = self.ssh.open_sftp()
            return True, "Connected successfully"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        if self.sftp:
            try: self.sftp.close()
            except: pass
        if self.ssh:
            try: self.ssh.close()
            except: pass

    def upload_file(self, local_path, remote_path):
        if not self.sftp:
            return False, "SFTP not initialized"
        
        # Ensure directories exist
        remote_dir = "/".join(remote_path.split('/')[:-1])
        try:
            self.sftp.stat(remote_dir)
        except IOError:
            # Simple recursive mkdir fallback
            dirs = remote_dir.split('/')
            curr = ""
            for d in dirs:
                if not d: continue
                curr += f"/{d}"
                try:
                    self.sftp.stat(curr)
                except IOError:
                    try:
                        self.sftp.mkdir(curr)
                    except:
                        pass

        try:
            self.sftp.put(local_path, remote_path)
            return True, f"Uploaded {local_path}"
        except Exception as e:
            return False, str(e)

    def execute_command(self, cmd, timeout=None):
        if not self.ssh:
            return False, "Not connected"
        try:
            # paramiko exec_command takes timeout argument on transport channel in newer versions, 
            # but we can set timeout on the channel
            t = self.ssh.get_transport()
            if not t or not t.is_active():
                return False, "SSH Transport not active"
            
            chan = t.open_session()
            chan.settimeout(timeout or self.timeout)
            chan.exec_command(cmd)
            
            out = chan.recv(4096).decode('utf-8', errors='ignore')
            err = chan.recv_stderr(4096).decode('utf-8', errors='ignore')
            
            while not chan.exit_status_ready():
                if chan.recv_ready():
                    out += chan.recv(4096).decode('utf-8', errors='ignore')
                if chan.recv_stderr_ready():
                    err += chan.recv_stderr(4096).decode('utf-8', errors='ignore')
            
            success = chan.recv_exit_status() == 0
            chan.close()
            return success, out + ("\n" + err if err else "")
        except Exception as e:
            return False, str(e)
