"""
[RU] Этот скрипт используется для проверки состояния игрового сервера.
Он читает стартовые скрипты и проверяет запущенные процессы.

[EN] This script is used to check the status of the game server.
It reads startup scripts and checks running processes.
"""
from config_manager import ConfigManager
from ssh_manager import SSHManager

# [RU] Загрузка настроек игрового сервера / [EN] Load game server settings
c = ConfigManager()
conf = c.get('game_server')

# [RU] Подключение по SSH / [EN] Connect via SSH
ssh = SSHManager(conf['host'], conf['user'], conf['password'])
ssh.connect()

# [RU] Чтение содержимого стартового скрипта / [EN] Read startup script contents
# Check start.sh contents
ok, out = ssh.execute_command('cat /root/mineroot/NoteBuns/start.sh')
print("=== start.sh ===")
print(out)

# [RU] Проверка запущенных screen-сессий / [EN] Check running screen sessions
# Check if screen session exists
ok, out = ssh.execute_command('screen -ls')
print("\n=== screen -ls ===")
print(out)

# [RU] Проверка процессов Java (сервер Minecraft) / [EN] Check Java processes (Minecraft server)
# Check running java processes
ok, out = ssh.execute_command('ps aux | grep java | grep -v grep')
print("\n=== java processes ===")
print(out)

# [RU] Отключение от сервера / [EN] Disconnect from server
ssh.disconnect()
