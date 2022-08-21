#!/bin/sh
set -eu
IMGS_DIR="/boot_disk/extra_container_modules"
ARCH="amd64"
mkdir -p /containers/mounts
mount -t tmpfs -o mode=0755 none /containers/mounts
mkdir /containers/mounts/mix_1 /containers/mounts/mix_2
mount -t squashfs -o ro,nosuid,nodev "$IMGS_DIR/mix_1_$ARCH.sqf" /containers/mounts/mix_1
mount -t squashfs -o ro,nosuid,nodev "$IMGS_DIR/mix_2_$ARCH.sqf" /containers/mounts/mix_2
