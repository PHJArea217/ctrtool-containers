#!/usr/bin/env python3
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('group');
parser.add_argument('-d', '--directory', default='/var/lib/_docker-in-ctrtool')
parser.add_argument('-C', '--cgroup-directory', default='/sys/fs/cgroup/d-in-ctrtool')
parser.add_argument('-R', '--run-directory', default='/run/_docker-in-ctrtool')
parser.add_argument('-s', '--setup', action='store_true')
args = parser.parse_args()
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
}''')
    with open(real_directory + '/init.py', 'w') as init_py:
        init_py.write('''#!/usr/bin/env python3
import ctypes, os, sys
libc = ctypes.CDLL(None)
libc.mount(b'none\\0', b'/sys/fs/cgroup\\0', b'cgroup2\\0', 0, None)
os.mkdir('/sys/fs/cgroup/init.scope',mode=0o777)
with open('/sys/fs/cgroup/init.scope/cgroup.procs', 'w') as cgroup_procs:
    cgroup_procs.write('1')
with open('/sys/fs/cgroup/cgroup.subtree_control', 'w') as cgroup_procs:
    cgroup_procs.write('+memory +pids')


args.directory = 
