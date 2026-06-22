import paramiko
import os

class SSHManager:
    """
    [RU] Менеджер SSH-подключений. Обеспечивает выполнение команд и SFTP-передачу файлов.
    [EN] SSH Connection Manager. Handles command execution and SFTP file transfers.
    """
    def __init__(self, host, user, password, timeout=5):
        """
        [RU] Конструктор класса. Инициализирует параметры подключения.
        [EN] Class constructor. Initializes connection parameters.
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
                look_for_keys=False,
                allow_agent=False
            )
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
        Использует каналы paramiko для установки индивидуального таймаута на команду.
        Возвращает кортеж (успех_булево, вывод_команды).
        
        [EN] Executes a console command on the remote server and collects output.
        Uses paramiko channels to set a custom timeout per command.
        Returns a tuple (success_boolean, command_output).
        """
        if not self.ssh:
            return False, "Not connected"
        try:
            # [RU] Получаем транспортный канал / [EN] Get transport channel
            t = self.ssh.get_transport()
            if not t or not t.is_active():
                return False, "SSH Transport not active"
            
            # [RU] Открываем сессию и устанавливаем таймаут / [EN] Open session and set timeout
            chan = t.open_session()
            chan.settimeout(timeout or self.timeout)
            chan.exec_command(cmd)
            
            # [RU] Читаем стандартный вывод и вывод ошибок / [EN] Read standard output and error output
            out = chan.recv(4096).decode('utf-8', errors='ignore')
            err = chan.recv_stderr(4096).decode('utf-8', errors='ignore')
            
            # [RU] Ждем завершения команды и дочитываем остатки / [EN] Wait for completion and read remaining chunks
            while not chan.exit_status_ready():
                if chan.recv_ready():
                    out += chan.recv(4096).decode('utf-8', errors='ignore')
                if chan.recv_stderr_ready():
                    err += chan.recv_stderr(4096).decode('utf-8', errors='ignore')
            
            # [RU] Успешно, если код возврата 0 / [EN] Success if exit code is 0
            success = chan.recv_exit_status() == 0
            chan.close()
            return success, out + ("\n" + err if err else "")
        except Exception as e:
            return False, str(e)
