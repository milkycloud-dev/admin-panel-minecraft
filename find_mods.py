from config_manager import ConfigManager
from ssh_manager import SSHManager

c = ConfigManager()

# DL Server
conf1 = c.get('download_server')
ssh1 = SSHManager(conf1['host'], conf1['user'], conf1['password'])
ssh1.connect()
ok, out = ssh1.execute_command('find /var/www/download.inflexus.world -type d -name "mods"')
print("DL Server Mods Paths:")
print(out)
