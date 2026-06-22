"""
[RU] Скрипт для тестирования путей на серверах.
Выполняет базовые проверки директорий на сервере загрузок и игровом сервере.

[EN] Script for testing paths on the servers.
Performs basic directory checks on the download server and game server.
"""
from config_manager import ConfigManager
from ssh_manager import SSHManager

# [RU] Загрузка конфигурации / [EN] Load configuration
c = ConfigManager()

# DL Server
# [RU] Настройка и подключение к серверу загрузок / [EN] Setup and connect to download server
conf1 = c.get('download_server')
ssh1 = SSHManager(conf1['host'], conf1['user'], conf1['password'])
ssh1.connect()

# [RU] Проверка наличия папки mods на сервере загрузок / [EN] Check for mods folder on download server
ok, out = ssh1.execute_command('ls -lA /var/www/download.inflexus.world/mods 2>/dev/null || echo "NOT_FOUND_DL"')
print("DL Server Mods Path (/var/www/download.inflexus.world/mods):")
print(out)

# [RU] Проверка содержимого корневой директории сервера загрузок / [EN] Check root directory contents of download server
ok, out = ssh1.execute_command('ls -lA /var/www/download.inflexus.world/ 2>/dev/null')
print("DL Server Root (/var/www/download.inflexus.world/):")
print(out)

# Game Server
# [RU] Настройка и подключение к игровому серверу / [EN] Setup and connect to game server
conf2 = c.get('game_server')
ssh2 = SSHManager(conf2['host'], conf2['user'], conf2['password'])
ssh2.connect()

# [RU] Проверка наличия папки mods на игровом сервере / [EN] Check for mods folder on game server
ok, out = ssh2.execute_command('ls -lA /root/mineroot/NoteBuns/mods 2>/dev/null || echo "NOT_FOUND_GAME"')
print("Game Server Mods Path (/root/mineroot/NoteBuns/mods):")
print(out)

# [RU] Проверка содержимого корневой директории игрового сервера / [EN] Check root directory contents of game server
ok, out = ssh2.execute_command('ls -lA /root/mineroot/NoteBuns/ 2>/dev/null')
print("Game Server Root (/root/mineroot/NoteBuns/):")
print(out)
