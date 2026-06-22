from config_manager import ConfigManager
from ssh_manager import SSHManager

c = ConfigManager()
conf = c.get('download_server')
ssh = SSHManager(conf['host'], conf['user'], conf['password'])
ssh.connect()

# Check what's in the client/mods directory — only .jar files?
ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/client/mods/ | head -20')
print("=== DL /client/mods/ (first 20) ===")
print(out)

# Check file types
ok, out = ssh.execute_command('ls /var/www/download.inflexus.world/client/mods/ | grep -v ".jar$" | head -20')
print("\n=== Non-.jar files ===")
print(out)

# Check manifest.json location
ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/client/manifest.json 2>/dev/null')
print("\n=== manifest.json in client/ ===")
print(out)

ok, out = ssh.execute_command('ls -la /var/www/download.inflexus.world/manifest.json 2>/dev/null')
print("\n=== manifest.json in root ===")
print(out)

# Check index.json
ok, out = ssh.execute_command('cat /var/www/download.inflexus.world/client/index.json 2>/dev/null | head -40')
print("\n=== index.json ===")
print(out)

ssh.disconnect()
