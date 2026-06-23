import sys
sys.path.append('.')
from config_manager import ConfigManager
from ssh_manager import SSHManager

c = ConfigManager()
gc = c.get('game_server')
ssh = SSHManager(gc['host'], gc['user'], gc['password'])
ok, msg = ssh.connect()
print('Connected:', ok, msg)
b_dir = f"{gc['remote_dir']}/backups"
b_name = 'test_backup.7z'
excl = c.get('backups', 'excluded_folders')
args = c.get('backups', '7z_args')
excl_cmd = ' '.join([f"-x!{f.strip()}" for f in excl.split(',') if f.strip()])
cmd = f"cd {gc['remote_dir']} && 7z a -bsp1 {args} {b_dir}/{b_name} ./* {excl_cmd}"
print('Command:', cmd)
ok, out = ssh.execute_command(cmd)
print('Output:', out)
ssh.disconnect()
