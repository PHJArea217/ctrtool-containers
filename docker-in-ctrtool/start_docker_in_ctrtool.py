#!/usr/bin/env python3
import argparse, os, sys, json, subprocess, ipaddress, ctypes
parser = argparse.ArgumentParser()
parser.add_argument('group');
parser.add_argument('-d', '--directory', default='/var/lib/_docker-in-ctrtool')
parser.add_argument('-C', '--cgroup-directory', default='/sys/fs/cgroup/d-in-ctrtool')
parser.add_argument('-R', '--run-directory', default='/run/_docker-in-ctrtool')
parser.add_argument('-s', '--setup', action='store_true')
parser.add_argument('-i', '--prepare', action='store_true')
args = parser.parse_args()
if args.prepare == True:
    try:
        os.mkdir(args.directory, mode=0o777)
    except:
        pass
    try:
        os.mkdir(args.cgroup_directory, mode=0o777)
    except:
        pass
    with open(args.cgroup_directory + '/cgroup.subtree_control', 'w') as cgroup_sc:
        cgroup_sc.write('+memory +pids')
    os.mkdir(args.run_directory, mode=0o777)
    subprocess.run(['ctrtool', 'mount_seq', '-m', args.run_directory, '-t', 'tmpfs', '-Osdx', '-omode=0755,size=10M', '-m', args.run_directory + '_host', '-E', '-s', args.run_directory, '-Obsdx', '-F8', '-r'], check=True)
    sys.exit(0)

if args.setup == True:
    real_directory = args.directory + '/g-' + args.group
    os.mkdir(real_directory, mode=0o777)
    os.mkdir(real_directory + '/rootfs', mode=0o700)
    os.mkdir(real_directory + '/rootfs/_root', mode=0o777)
    with open(real_directory + '/config.json', 'w') as config_json:
        config_json.write('''{
        "configured" false,
        "root_uid": 100000,
        "root_gid": 100000,
        "uid_map": "0.100000.100000",
        "gid_map": "0.100000.100000",
        "route_ipv4": ["172.20.0.0/20"],
        "route_ipv6": ["2001:db8:0:1:300::/72"],
        "ipv4": ["172.20.0.1"],
        "ipv6": ["2001:db8:0:1:300::1"],
        "net_iface_ip": ["172.19.255.1"],
        "net_iface": "vif0",
        "files": [
            ["/etc/passwd", {"mode": "755"}, "root:x:0:0:root:/root:/bin/bash\\n"],
            ["/etc/group", {}, "root:x:0:0:root:/root:/bin/bash\\n"]
        ],
        "hostname": "docker-in-ctrtool"
}''')
    with open(real_directory + '/init.py', 'w') as init_py:
        init_py.write('''#!/usr/bin/env python3
import ctypes, os, sys, json
libc = ctypes.CDLL(None)
libc.mount(b'none\\0', b'/sys/fs/cgroup\\0', b'cgroup2\\0', 0, None)
os.mkdir('/sys/fs/cgroup/init.scope',mode=0o777)
with open('/sys/fs/cgroup/init.scope/cgroup.procs', 'w') as cgroup_procs:
    cgroup_procs.write(f'1\\n{os.getpid()}\\n')
with open('/sys/fs/cgroup/cgroup.subtree_control', 'w') as cgroup_procs:
    cgroup_procs.write('+memory +pids')
config_json = json.load(open('/run/d-in-c-config/config.json', 'r'))
os.umask(0o077)
for f in config_json['files']:
    if 'type' in f[1]:
        if f[1]['type'] == 'dir':
            os.mkdir(f[0], mode=0o755)
            if 'mode' in f[1]:
                os.chmod(f[0], int(f[1].mode, base=8))
            continue
    with open(f[0], 'w') as the_file:
        the_file.write(f[2])
        if 'mode' in f[1]:
            os.fchmod(the_file.fileno(),int(f[1].mode, base=8))

''')
    sys.exit(0)

real_directory = args.directory + '/g-' + args.group
real_cgdir = args.cgroup_directory + '/g-' + args.group
real_rundir = args.run_directory + '/g-' + args.group
os.putenv('D_IN_C_DIR', real_directory)
os.putenv('D_IN_C_CGDIR', real_cgdir)
os.putenv('D_IN_C_RUNDIR', real_rundir)
config = json.load(open(real_directory + '/config.json', 'r'))
if config['configured'] != True:
    sys.stderr.write(f'{real_directory} not configured\n')
    sys.exit(1)
os.chown(real_directory + '/rootfs', -1, config['root_gid'])
os.chmod(real_directory + '/rootfs', 0o750)
os.chown(real_directory + '/rootfs/_root', config['root_uid'], config['root_gid'])
subprocess.run(['find', real_cgdir, '-depth', '-type', 'd', '-exec', 'rmdir', '--', '{}', '+'])
os.mkdir(real_cgdir, mode=0o777)
os.chown(real_cgdir, config['root_uid'], config['root_gid'])
os.chown(real_cgdir + '/cgroup.procs', config['root_uid'], config['root_gid'])
os.chown(real_cgdir + '/cgroup.subtree_control', config['root_uid'], config['root_gid'])
try:
    os.mkdir(real_rundir, mode=0o777)
except:
    pass
os.chown(real_rundir, config['root_uid'], config['root_gid'])
networks = []
local_ip = []
for n in config['ipv4']:
    networks.append(ipaddress.IPv4Network(n))
for n in config['route_ipv4']:
    networks.append(ipaddress.IPv4Network(n))
for n in config['ipv6']:
    networks.append(ipaddress.IPv6Network(n))
for n in config['route_ipv6']:
    networks.append(ipaddress.IPv6Network(n))
for n in config['net_iface_ip']:
    local_ip.append(ipaddress.ip_address(n))
os.putenv('D_IN_C_IFACE', config['net_iface'])
os.putenv('D_IN_C_NETWORKS', ' '.join(str(n) for n in networks))
os.putenv('D_IN_C_LOCAL', ' '.join(str(n) for n in local_ip))
os.execvp('ctrtool', ['ctrtool', 'launcher', '-U', '--escape', '--alloc-tty', '--uid-map=' + config['uid_map'], '--gid-map=' + config['gid_map'], '-Cimnpu', '--hostname=' + config['hostname'],f'--write-pid={real_cgdir}/cgroup.procs', '--script-is-shell', '''--script=/bin/true;set -eu
cd "/proc/self/fd/$2/ns"
nsenter --user=user --ipc=ipc --mount=mnt --net=net sh -eu -c '
ctrtool rootfs-mount -o root_link_opts=usr_ro -o root_symlink_usr=1 -o mount_sysfs=1 /proc/driver
cd /proc/driver
ctrtool mount_seq -m "_fsroot_rw" -E -s "$D_IN_C_DIR/rootfs/_root" -Obv -m "run/host_shared" -E -s "$D_IN_C_RUNDIR" -Ob -D _fsroot_ro -M 0755 -m "_fsroot_ro/usr" -E -s /usr -Obv
mkdir run/d-in-c-config
cp "$D_IN_C_DIR/config.json" "$D_IN_C_DIR/init.py" run/d-in-c-config/
if [ -x "$D_IN_C_DIR/setup_mount" ]; then "$D_IN_C_DIR/setup_mount"; fi
'
ip link add name "$D_IN_C_IFACE" type veth peer name eth0 netns "/proc/self/fd/$2/ns/net"
for n in $D_IN_C_LOCAL fe80::1; do ip addr add "$n" dev "$D_IN_C_IFACE"; done
ip link set dev "$D_IN_C_IFACE" up
for n in $D_IN_C_NETWORKS;do ip route add "$n" via inet6 "fe80::2" dev "$D_IN_C_IFACE";done
                      ''', '-V', '--mount-proc', '--pivot-root=/proc/driver', '/bin/sh', '-c', 'exec /bin/bash 2>&1'])
# args.directory = 
