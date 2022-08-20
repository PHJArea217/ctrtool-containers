#!/usr/bin/python3
import os, sys, subprocess

if len(sys.argv) < 7:
    sys.stderr.write(f'Usage: {sys.argv[0]} [rootfs.tar.gz] [install_dir] [uid map] [gid map] [root_uid] [root_gid]')
    sys.exit(1)

rootfs_tar = sys.argv[1]
install_dir = sys.argv[2]
uid_map = sys.argv[3]
gid_map = sys.argv[4]
root_uid = int(sys.argv[5])
root_gid = int(sys.argv[6])

current_arg = None
extra_args = {}

for arg in sys.argv[7:]:
    if current_arg == None:
        current_arg = arg
    else:
        extra_args[current_arg] = arg
        current_arg = None

for _char in uid_map + gid_map:
    if _char not in "0123456789.:":
        sys.stderr.write(f'Invalid character {_char} in UID/GID map')
        sys.exit(1)

os.mkdir(install_dir)
os.mkdir(install_dir + "/rootfs", mode=0o700)
os.chown(install_dir + "/rootfs", root_uid, root_gid)
os.mkdir(install_dir + "/rootfs/_root", mode=0o755)
os.chown(install_dir + "/rootfs/_root", root_uid, root_gid)

ctrtool_path = extra_args['ctrtool'] if 'ctrtool' in extra_args else 'ctrtool'
selected_snippets = extra_args['snippets'].split(',') if 'snippets' in extra_args else []
flags = extra_args['flags'].split(',') if 'flags' in extra_args else []
if 'netns_ambient' in flags:
    netns_switch = 'unshare -n'
    netns_flag = ''
else:
    netns_switch = '--net="/proc/self/fd/$2/ns/net"'
    netns_flag = 'n'
if 'netns_veth_name' in extra_args:
    netns_veth = f'ip link add name "{netns_veth_name}" type veth peer name eth0 netns /proc/self/fd/"$2"/root/proc/driver/run/netns/__host__\n'
else:
    netns_veth = ''

if rootfs_tar != "/dev/null":
    subprocess.run([ctrtool_path, 'launcher', '-U', '--escape', '--uid-map=' + uid_map, '--gid-map=' + gid_map, '-sw', 'bsdtar', '-xC', install_dir + '/rootfs/_root', '-f', rootfs_tar], check=True)

install_dir_realpath = os.path.realpath(install_dir)

with open(install_dir + "/start.py", 'w') as start_script:
    start_script.write('''#!/usr/bin/python3
import os
ctrtool = """''' + ctrtool_path + '''"""
os.environ['CTRTOOL'] = ctrtool
os.execv(ctrtool, ['launcher', '-U', '--escape', '--uid-map=''' + uid_map + '''', '--gid-map=''' + gid_map + '''', '-s', '-w', '--script-is-shell', '-V', """--script=/bin/true;set -eu
nsenter --user="/proc/self/fd/$2/ns/user" --ipc="/proc/self/fd/$2/ns/ipc" --mount="/proc/self/fd/$2/ns/mnt" ''' + netns_switch + ''' sh -c 'set -eu
"$CTRTOOL" rootfs-mount -o root_link_opts=all_rw -o mount_sysfs=1 /proc/driver
"$CTRTOOL" mount_seq -c /proc/driver -m _fsroot_rw -E -s "$1/rootfs/_root" -Obv -D run/netns -M 0755 -m run/netns/__host__ -f -s /proc/self/ns/net -K -Ob
' _ ''' + "'" + install_dir_realpath + "'" + '''
""", '--alloc-tty', '--wait', '-mpCiu''' + netns_flag + '''', '--hostname=my-ctrtool-container', '-t', '-r/proc/driver', '/bin/bash'])
''')
    os.fchmod(start_script.fileno(), 0o755)
