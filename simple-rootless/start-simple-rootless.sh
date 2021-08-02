#!/bin/sh
set -eu
: ${SQUASHFS_MOUNT_PREFIX:=/ctr_fs1}
: ${SQUASHFS_IMG_NAME:=generic}
: ${CTRTOOL:=$SQUASHFS_MOUNT_PREFIX/_system/bin/ctrtool}
: ${CONTAINER_HOME:=~/.local/share/ctrtool-containers/generic}
mkdir -p "$CONTAINER_HOME"
export SQUASHFS_MOUNT_PREFIX SQUASHFS_IMG_NAME CTRTOOL CONTAINER_HOME

exec "$CTRTOOL" launcher --escape -U -m -n -p -C -i -u --mount-proc --pivot-root=/proc/driver --alloc-tty --script-is-shell --script='/bin/true;set -eu
cd /proc/self/fd/"$2"/ns
nsenter --user=user --net=net --ipc=ipc --mount=mnt --preserve-credentials sh -c '\''set -eu
"$CTRTOOL" rootfs-mount -o root_link_opts=usr_ro -o root_symlink_usr=1 -o mount_sysfs=1 /proc/driver
"$CTRTOOL" mount_seq -c /proc/driver -m _fsroot_ro -E -s "$SQUASHFS_MOUNT_PREFIX/$SQUASHFS_IMG_NAME" -Obvosd -r -m _fsroot_rw -E -s "$CONTAINER_HOME" -Obv
'\''
' --uid-map="0.`id -u`.1" --gid-map="0.`id -g`.1" --disable-setgroups --no-clear-groups sh -c 'exec /bin/busybox ash 2>&1'
