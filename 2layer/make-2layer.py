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

subprocess.run([ctrtool_path, 'launcher', '-U', '--escape', '--uid-map=' + uid_map, '--gid-map=' + gid_map, '-sw', 'bsdtar', '-xC', install_dir + '/rootfs/_root', '-f', rootfs_tar], check=True)

install_dir_realpath = os.path.realpath(install_dir)

with open(install_dir + "/start.py", 'w') as start_script:
    start_script.write('''#!/usr/bin/python3
import os
ctrtool = """''' + ctrtool_path + '''"""
os.environ['CTRTOOL'] = ctrtool
os.execv(ctrtool, ['launcher', '-U', '--escape', '--uid-map=''' + uid_map + '''', '--gid-map=''' + gid_map + '''', '-s', '-w', '--script-is-shell', '-V', """--script=/bin/true;set -eu
nsenter --user="/proc/self/fd/$2/ns/user" --net="/proc/self/fd/$2/ns/net" --ipc="/proc/self/fd/$2/ns/ipc" --mount="/proc/self/fd/$2/ns/mnt" sh -c 'set -eu
"$CTRTOOL" rootfs-mount -o root_link_opts=all_rw -o mount_sysfs=1 /proc/driver
"$CTRTOOL" mount_seq -c /proc/driver -m _fsroot_rw -E -s "$1/rootfs/_root" -Obv
' _ ''' + "'" + install_dir_realpath + "'" + '''
""", '--alloc-tty', '--wait', '-nmpCiu', '--hostname=my-ctrtool-container', '-t', '-r/proc/driver', '/bin/bash'])
''')
    os.fchmod(start_script.fileno(), 0o755)
