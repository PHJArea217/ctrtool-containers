#!/usr/bin/python3
import os, sys, subprocess

if len(sys.argv) < 7:
    sys.stderr.write(f'Usage: {sys.argv[0]} [rootfs.tar.gz] [install_dir] [uid map] [gid map] [root_uid] [root_gid]\n')
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
os.mkdir(install_dir + "/rootfs", mode=0o750)
os.chown(install_dir + "/rootfs", -1, root_gid)
os.mkdir(install_dir + "/rootfs/_root", mode=0o755)
os.chown(install_dir + "/rootfs/_root", root_uid, root_gid)
os.mkdir(install_dir + "/config_dir", mode=0o700)

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
    netns_veth_name = extra_args['netns_veth_name']
    netns_veth = f'ip link add name "{netns_veth_name}" type veth peer name eth0 netns /proc/self/fd/"$2"/root/proc/driver/run/netns/__host__\n'
    if 'netns_veth_extra_config' in selected_snippets:
        netns_veth = netns_veth + f'''
ip addr add 192.0.0.8 dev "{netns_veth_name}"
ip link set dev "{netns_veth_name}" address 00:00:5e:00:53:42 up
ip route add 192.0.2.0/24 via inet6 fe80::200:5eff:fe00:5343 dev "{netns_veth_name}"
'''
else:
    netns_veth = ''
if 'mix_mounts' in selected_snippets:
    mix_mounts = '-m ctr_fs1 -E -s /containers/mounts/mix_1 -Obvsdo -r -m ctr_fs2 -E -s /containers/mounts/mix_2 -Obvsdo -r'
else:
    mix_mounts = ''

install_dir_realpath = os.path.realpath(install_dir)

if 'extract_config_tar' in selected_snippets:
    extract_config_tar = f'''cd /proc/driver; rm etc; mkdir etc; bsdtar -xC etc -f '{install_dir_realpath}/rootfs/config_tar.tgz'\n'''
else:
    extract_config_tar = ''
if 'init' in flags:
    container_init = "'/bin/sh', '-c', '/etc/__init__; exec /bin/bash'"
else:
    container_init = "'/bin/bash'"

if rootfs_tar != "/dev/null":
    subprocess.run([ctrtool_path, 'launcher', '-U', '--escape', '--uid-map=' + uid_map, '--gid-map=' + gid_map, '-sw', 'bsdtar', '-xC', install_dir + '/rootfs/_root', '-f', rootfs_tar], check=True)

with open(install_dir + "/start.py", 'w') as start_script:
    start_script.write('''#!/usr/bin/python3
import os
ctrtool = """''' + ctrtool_path + '''"""
os.environ['CTRTOOL'] = ctrtool
os.execvp(ctrtool, ['launcher', '-U', '--escape', '--uid-map=''' + uid_map + '''', '--gid-map=''' + gid_map + '''', '-s', '-w', '--script-is-shell', '-V', """--script=/bin/true;set -eu
nsenter --user="/proc/self/fd/$2/ns/user" --ipc="/proc/self/fd/$2/ns/ipc" --mount="/proc/self/fd/$2/ns/mnt" ''' + netns_switch + ''' sh -c 'set -eu
"$CTRTOOL" rootfs-mount -o root_link_opts=all_rw -o mount_sysfs=1 /proc/driver
"$CTRTOOL" mount_seq -c /proc/driver -m _fsroot_rw -E -s "$1/rootfs/_root" -Obv \\
''' + mix_mounts + ''' \\
-D run/netns -M 0755 -m run/netns/__host__ -f -s /proc/self/ns/net -K -Ob
''' + extract_config_tar + '''
' _ ''' + "'" + install_dir_realpath + "'" + '''
''' + netns_veth + '''
""", '--alloc-tty', '--wait', '-mpCiu''' + netns_flag + '''', '--hostname=my-ctrtool-container', '-t', '-r/proc/driver', '''+container_init+'''])
''')
    os.fchmod(start_script.fileno(), 0o755)
with open(install_dir + "/make_config_tar.sh", 'w') as make_config_tar:
    make_config_tar.write("""#!/bin/sh\nset -eu
INSTALL_DIR='"""+install_dir_realpath+"""'
CONFIG_DIR="${1:-$INSTALL_DIR/config_dir}"
umask 077
tar -c -C "$CONFIG_DIR" . | gzip -9c > "$INSTALL_DIR/rootfs/config_tar.tgz.tmp"
chgrp '""" + str(root_gid) + """' "$INSTALL_DIR/rootfs/config_tar.tgz.tmp"
chmod 0640 "$INSTALL_DIR/rootfs/config_tar.tgz.tmp"
mv -n "$INSTALL_DIR/rootfs/config_tar.tgz.tmp" "$INSTALL_DIR/rootfs/config_tar.tgz"
""")
    os.fchmod(make_config_tar.fileno(), 0o755)
