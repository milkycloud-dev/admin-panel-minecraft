"""
[RU] Скрипт для поиска папок с модами на сервере.
[EN] Script for finding mod folders on the server.
"""
from config_manager import ConfigManager
from ssh_manager import SSHManager

# [RU] Загрузка конфигурации / [EN] Load configuration
c = ConfigManager()

# DL Server
# [RU] Получение параметров сервера загрузок / [EN] Get download server parameters
conf1 = c.get('download_server')
ssh1 = SSHManager(conf1['host'], conf1['user'], conf1['password'])
ssh1.connect()

# [RU] Выполнение команды поиска папок с именем "mods" / [EN] Execute command to find folders named "mods"
ok, out = ssh1.execute_command('find /var/www/download.inflexus.world -type d -name "mods"')
print("DL Server Mods Paths:")
print(out)
