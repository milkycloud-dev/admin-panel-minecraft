from config_manager import ConfigManager
from ssh_manager import SSHManager

c = ConfigManager()
conf = c.get('game_server')
ssh = SSHManager(conf['host'], conf['user'], conf['password'])
ssh.connect()

# Check start.sh contents
ok, out = ssh.execute_command('cat /root/mineroot/NoteBuns/start.sh')
print("=== start.sh ===")
print(out)

# Check if screen session exists
ok, out = ssh.execute_command('screen -ls')
print("\n=== screen -ls ===")
print(out)

# Check running java processes
ok, out = ssh.execute_command('ps aux | grep java | grep -v grep')
print("\n=== java processes ===")
print(out)

ssh.disconnect()
