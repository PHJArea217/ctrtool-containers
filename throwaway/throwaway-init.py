#!/usr/bin/python3

import os, subprocess, socket, sys

throwaway_username = sys.argv[1]

if os.getpid() != 1:
    raise OSError

for letter in throwaway_username:
    if letter in "0123456789abcdefghijklmnopqrstuvwxyz-_":
        pass
    else:
        raise OSError("Invalid characters in username")

sys_users = [
        ("root", 0, 0, "/root", "/usr/sbin/nologin"),
        ("syslog", 100, 100, "/var/spool/rsyslog", "/usr/sbin/nologin"),
        ("sshd", 101, 101, "/run/sshd", "/usr/sbin/nologin"),
        ("nobody", 103, 103, "/none", "/usr/sbin/nologin"),
        (throwaway_username, 1000, 1000, '/home/' + throwaway_username, "/bin/bash")
]

sys_groups = [
        ("root", 0, []),
        ("syslog", 100, [throwaway_username]),
        ("sshd", 101, []),
        ("nogroup", 103, []),
        (throwaway_username, 1000, [])
]

os.unlink("/etc")
os.mkdir("/etc", 0o755)
os.mkdir("/etc/timidity", 0o755)

os.umask(0o077)
with open("/etc/passwd", "x") as passwd_file, open("/etc/shadow", "x") as shadow_file:
    for user, uid, gid, home, user_shell in sys_users:
        passwd_file.write(f"{user}:x:{uid}:{gid}:{user}:{home}:{user_shell}\n")
        shadow_file.write(f"{user}:*:18700:0:99999:7:::\n")

with open("/etc/group", "x") as group_file, open("/etc/gshadow", "x") as gshadow_file:
    for group, gid, userlist in sys_groups:
        group_file.write("%s:x:%d:%s\n" % (group, gid, ','.join(userlist)))
        gshadow_file.write(f"{group}:*::\n")

os.chmod("/etc/passwd", 0o644)
os.chmod("/etc/group", 0o644)

os.umask(0o022)

os.mkdir("/run/sshd", 0o755)

os.unlink("/home")
os.symlink("/_pdisk/tb-home", "/home")

os.unlink("/var")
os.mkdir("/var", 0o755)
os.mkdir("/var/spool", 0o755)
os.mkdir("/var/spool/rsyslog", 0o755)
os.chown("/var/spool/rsyslog", 100, 100)
os.symlink("/_pdisk/tb-logs", "/var/log")

os.mkdir("/var/tmp")
os.chmod("/var/tmp", 0o1777)

os.symlink("/run", "/var/run")

try:
    os.mkdir("/_pdisk/tb-home", 0o0755)
except:
    pass
try:
    os.mkdir("/home/" + throwaway_username, 0o0700)
except:
    pass
os.chown("/home/" + throwaway_username, 1000, 1000)

try:
    os.mkdir("/_pdisk/tb-logs")
except:
    pass
os.chown("/_pdisk/tb-logs", 100, 100)

for dir_ in ["alsa", "alternatives", "nsswitch.conf", "pam.d", "security", "ssl"]:
    os.symlink("/_throwaway_root/throwaway/etc/" + dir_, "/etc/" + dir_)

for dir_ in ["ssh"]:
    os.symlink("/_throwaway_config/" + dir_, "/etc/" + dir_)

with open("/etc/inittab", "x") as inittab_file:
    inittab_file.write("""::respawn:/usr/sbin/sshd -D\n""")

dev_log_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
dev_log_socket.bind("/dev/log")
os.chmod("/dev/log", 0o777)


subprocess.Popen(["setpriv", "--reuid=syslog", "--regid=syslog", "--clear-groups", "/_throwaway_root/_system/bin/ctrtool", "syslogd"], stdin=dev_log_socket)

subprocess.run("if [ -r /_throwaway_config/init.local ]; then . /_throwaway_config/init.local; fi", shell=True, check=True)

os.system('set -eu; cd /etc; for dir in /_throwaway_root/throwaway/etc/*; do if [ ! -h "${dir##*/}" ] && [ ! -e "${dir##*/}" ]; then ln -s "$dir" >/dev/null 2>&1 || :; fi; done')
os.execv("/_throwaway_root/_system/bin/busybox-d", ['init'])
