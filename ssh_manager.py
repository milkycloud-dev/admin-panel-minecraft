import paramiko
import os

class SSHManager:
    """
    [RU] Менеджер SSH-подключений. Обеспечивает выполнение команд и SFTP-передачу файлов.
    [EN] SSH Connection Manager. Handles command execution and SFTP file transfers.
    """
    def __init__(self, host, user, password, timeout=20):
        """
        [RU] Конструктор класса. Инициализирует параметры подключения.
        timeout — секунды на TCP/баннер (раньше 5с давало ложные обрывы на нестабильном канале).
        [EN] Constructor. timeout is TCP/banner seconds (was 5s — flaky on unstable links).
        """
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.ssh = None
        self.sftp = None

    def connect(self):
        """
        [RU] Устанавливает SSH соединение и открывает SFTP сессию.
        Использует AutoAddPolicy для автоматического принятия ключей хоста.
        Возвращает кортеж (успех_булево, сообщение).
        
        [EN] Establishes an SSH connection and opens an SFTP session.
        Uses AutoAddPolicy to automatically accept host keys.
        Returns a tuple (success_boolean, message).
        """
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.host, 
                username=self.user, 
                password=self.password, 
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )
            transport = self.ssh.get_transport()
            if transport is not None:
                transport.set_keepalive(30)
            self.sftp = self.ssh.open_sftp()
            return True, "Connected successfully"
        except Exception as e:
            # [RU] Если произошла ошибка при подключении, закрываем сокеты / [EN] Close sockets on connection error
            self.disconnect()
            return False, str(e)

    def disconnect(self):
        """
        [RU] Безопасно закрывает SFTP и SSH сессии, если они открыты.
        [EN] Safely closes SFTP and SSH sessions if they are open.
        """
        if self.sftp:
            try: self.sftp.close()
            except: pass
        if self.ssh:
            try: self.ssh.close()
            except: pass

    def upload_file(self, local_path, remote_path):
        """
        [RU] Загружает локальный файл на удаленный сервер по протоколу SFTP.
        Автоматически создает необходимые директории на сервере, если их нет.
        Возвращает кортеж (успех_булево, сообщение).
        
        [EN] Uploads a local file to the remote server via SFTP protocol.
        Automatically creates necessary directories on the server if they are missing.
        Returns a tuple (success_boolean, message).
        """
        if not self.sftp:
            return False, "SFTP not initialized"
        
        # [RU] Получаем путь к директории из полного пути / [EN] Extract directory path from full path
        remote_dir = "/".join(remote_path.split('/')[:-1])
        try:
            # [RU] Проверяем существование папки / [EN] Check if directory exists
            self.sftp.stat(remote_dir)
        except IOError:
            # [RU] Простой рекурсивный метод создания папок / [EN] Simple recursive mkdir fallback
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
            # [RU] Отправка файла / [EN] Upload the file
            self.sftp.put(local_path, remote_path)
            return True, f"Uploaded {local_path}"
        except Exception as e:
            return False, str(e)

    def execute_command(self, cmd, timeout=None):
        """
        [RU] Выполняет консольную команду на удаленном сервере и собирает вывод.
        [EN] Executes a console command on the remote server and collects output.
        """
        if not self.ssh:
            return False, "Not connected"
        try:
            effective_timeout = timeout or self.timeout
            stdin, stdout, stderr = self.ssh.exec_command(cmd, timeout=effective_timeout)
            channel = stdout.channel
            if effective_timeout:
                channel.settimeout(effective_timeout)
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            exit_code = channel.recv_exit_status()
            combined = out + (f"\n{err}" if err.strip() else "")
            return exit_code == 0, combined
        except Exception as e:
            return False, str(e)

    def download_file(self, remote_path, local_path):
        """Download remote file via SFTP. Returns (success, message)."""
        if not self.sftp:
            return False, "SFTP not initialized"
        try:
            local_dir = os.path.dirname(os.path.abspath(local_path))
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
            self.sftp.get(remote_path, local_path)
            return True, f"Downloaded {remote_path}"
        except Exception as e:
            return False, str(e)
