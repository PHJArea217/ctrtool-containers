#!/usr/bin/python3

import os, json, sys
config_json = json.load(open(sys.argv[1], 'r'))

ctrtool_path = os.environ['CTRTOOL'] if 'CTRTOOL' in os.environ else '/__autoserver__/ctrtool'

os.environ['CTRTOOL'] = ctrtool_path

uid_map = int(config_json['uid_start'])
gid_map = int(config_json['gid_start'])
userns_owner_uid = int(config_json['userns_owner_uid']) if 'userns_owner_uid' in config_json else None

throwaway_pdisk = str(config_json['pdisk_path'])
os.environ['THROWAWAY_PDISK_PATH'] = throwaway_pdisk

# throwaway_log = str(config_json['log'])

throwaway_mac = str(config_json['mac_address'])
os.environ['THROWAWAY_MAC_ADDRESS'] = throwaway_mac
throwaway_ip = str(config_json['ip'])
os.environ['THROWAWAY_IP_ADDRESS'] = throwaway_ip

throwaway_hostname = str(config_json['hostname']) if 'hostname' in config_json else 'throwaway'

throwaway_username = str(config_json['username'])

os.environ['THROWAWAY_CONFIG_BUNDLE'] = config_json['config_bundle'] if 'config_bundle' in config_json else ""

if 'THROWAWAY_MOUNT_PATH' not in os.environ:
    os.environ['THROWAWAY_MOUNT_PATH'] = '/container_images/ctr_fs4'

os.environ['THROWAWAY_UID_NR'] = hex(uid_map)

ctrtool_launcher_options = ['launcher', '--escape', '-VsUnmpiutr/proc/driver',
        '--uid-map=0.%d.1:100.%d.4:1000.%d.5' % (uid_map, uid_map + 1, uid_map + 5),
        '--gid-map=0.%d.1:100.%d.4:1000.%d.5' % (gid_map, gid_map + 1, gid_map + 5),
        '--script-is-shell', '''--script=/bin/true; set -eu
ip link add vt_"$THROWAWAY_UID_NR" type veth peer name eth0 netns "/proc/self/fd/$2/ns/net"
ip link set vt_"$THROWAWAY_UID_NR" address 00:00:5e:00:53:f0 master br-throw up
cd /proc/self/fd/"$2"/ns
nsenter --user=user --net=net --ipc=ipc --mount=mnt sh -s <<\\EOF
set -eu
"$CTRTOOL" rootfs-mount -o root_link_opts=usr_ro -o root_symlink_usr=1 -o mount_sysfs=1 /proc/driver
"$CTRTOOL" mount_seq -c /proc/driver \
        -m _throwaway_root -E -s "$THROWAWAY_MOUNT_PATH" -r -Obosd \
        -m ctr_fs1 -E -s /container_images/ctr_fs1 -r -Obosd \
        -m ctr_fs2 -E -s /container_images/ctr_fs2 -r -Obosd \
        -m _pdisk -E -s "$THROWAWAY_PDISK_PATH" -Ob \
        -l _fsroot_ro -s _throwaway_root/throwaway \
        -D _fsroot_rw -M 0755 \
        -D _throwaway_config -M 0755
if [ -n "${THROWAWAY_CONFIG_BUNDLE}" ]; then
    bsdtar -x --no-same-owner -C /proc/driver/_throwaway_config -f "$THROWAWAY_CONFIG_BUNDLE"
fi
cp /throwaway_lib/throwaway-init.py /proc/driver/init.py
chmod +x /proc/driver/init.py
ip link set lo up
for x in $THROWAWAY_IP_ADDRESS; do
    ip addr add "$x" dev eth0
done
ip link set eth0 address "$THROWAWAY_MAC_ADDRESS" up
ip route add ::/0 via fe80::300:0:0:1 dev eth0
ip route add 0.0.0.0/0 via inet6 fe80::300:0:0:1 dev eth0
EOF
''', '-b0xc85fb', '--hostname=' + throwaway_hostname]

if userns_owner_uid != None:
    ctrtool_launcher_options += ['-O%d' % userns_owner_uid]

if 'THROWAWAY_DEBUG' in os.environ and os.environ['THROWAWAY_DEBUG'] == '1':
    ctrtool_launcher_options += ['--alloc-tty', '/_throwaway_root/_system/bin/busybox-d', 'ash']
else:
    # FIXME: In the final product, init.py will be part of _throwaway_root.
    ctrtool_launcher_options += ['--log-file=/dev/null', '/_throwaway_root/_system/bin/busybox-d', 'sh', '-c', 'set -eu; exec /init.py "$1" </dev/null >>/_pdisk/throwaway.log 2>&1', '-', throwaway_username]

os.execv(ctrtool_path, ctrtool_launcher_options)
