from config_manager import ConfigManager
from ssh_manager import SSHManager

c = ConfigManager()

# DL Server
conf1 = c.get('download_server')
ssh1 = SSHManager(conf1['host'], conf1['user'], conf1['password'])
ssh1.connect()
ok, out = ssh1.execute_command('ls -lA /var/www/download.inflexus.world/mods 2>/dev/null || echo "NOT_FOUND_DL"')
print("DL Server Mods Path (/var/www/download.inflexus.world/mods):")
print(out)

ok, out = ssh1.execute_command('ls -lA /var/www/download.inflexus.world/ 2>/dev/null')
print("DL Server Root (/var/www/download.inflexus.world/):")
print(out)

# Game Server
conf2 = c.get('game_server')
ssh2 = SSHManager(conf2['host'], conf2['user'], conf2['password'])
ssh2.connect()
ok, out = ssh2.execute_command('ls -lA /root/mineroot/NoteBuns/mods 2>/dev/null || echo "NOT_FOUND_GAME"')
print("Game Server Mods Path (/root/mineroot/NoteBuns/mods):")
print(out)

ok, out = ssh2.execute_command('ls -lA /root/mineroot/NoteBuns/ 2>/dev/null')
print("Game Server Root (/root/mineroot/NoteBuns/):")
print(out)
