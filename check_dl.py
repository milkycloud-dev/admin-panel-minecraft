"""
[RU] Этот скрипт используется для проверки файлов модов на сервере загрузок.
Он подключается по SSH и выполняет команды для просмотра содержимого директорий.

[EN] This script is used to check mod files on the download server.
It connects via SSH and executes commands to view directory contents.
"""
from config_manager import ConfigManager
from ssh_manager import SSHManager

# [RU] Инициализация менеджера конфигурации / [EN] Initialize configuration manager
c = ConfigManager()
# [RU] Получение настроек сервера загрузок / [EN] Get download server settings
conf = c.get('download_server')

# [RU] Создание SSH-менеджера и подключение / [EN] Create SSH manager and connect
ssh = SSHManager(conf['host'], conf['user'], conf['password'])
ssh.connect()

# [RU] Проверка содержимого папки модов / [EN] Check mods folder contents
# Check what's in the client/mods directory — only .jar files?
ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/client/mods/ | head -20')
print("=== DL /client/mods/ (first 20) ===")
print(out)

# [RU] Проверка наличия других файлов кроме .jar / [EN] Check for non-.jar files
# Check file types
ok, out = ssh.execute_command('ls /var/www/download.inflexus.world/client/mods/ | grep -v ".jar$" | head -20')
print("\n=== Non-.jar files ===")
print(out)

# [RU] Проверка местоположения манифеста / [EN] Check manifest location
# Check manifest.json location
ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/client/manifest.json 2>/dev/null')
print("\n=== manifest.json in client/ ===")
print(out)

ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/manifest.json 2>/dev/null')
print("\n=== manifest.json in root ===")
print(out)

# [RU] Чтение файла индекса / [EN] Read index file
# Check index.json
ok, out = ssh.execute_command('cat /var/www/download.inflexus.world/client/index.json 2>/dev/null | head -40')
print("\n=== index.json ===")
print(out)

# [RU] Отключение от сервера / [EN] Disconnect from server
ssh.disconnect()
