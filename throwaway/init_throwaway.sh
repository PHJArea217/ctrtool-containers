#!/bin/sh

set -eu

mkdir -p /container_images/ctr_fs4 \
	/container_images/ctr_fs2 \
	/container_images/ctr_fs1 \
	/disk

mount -t squashfs -o ro,nosuid,nodev \
	"${THROWAWAY_MODULE_FILE:=/boot_disk/extra_container_modules/mix_4_amd64.sqf}" \
	"${THROWAWAY_MOUNT_PATH:=/container_images/ctr_fs4}"

mount -t squashfs -o ro,nosuid,nodev /boot_disk/extra_container_modules/mix_1_amd64.sqf /container_images/ctr_fs1
mount -t squashfs -o ro,nosuid,nodev /boot_disk/extra_container_modules/mix_2_amd64.sqf /container_images/ctr_fs2
mount -t ext4 -o nosuid,nodev /dev/sda /disk

mkdir -p /disk/throwaway_1_1 /disk/throwaway_1_2 /disk/throwaway_1_3 /disk/throwaway_2_1 /disk/throwaway_2_2
chown 66000:66000 /disk/throwaway_1_1 /disk/throwaway_2_1
chown 66010:66010 /disk/throwaway_1_2 /disk/throwaway_2_2
chown 66020:66020 /disk/throwaway_1_3

sysctl -w net.ipv6.conf.ens3.accept_ra=0 net.ipv6.conf.all.accept_ra=0 net.ipv6.conf.default.accept_ra=0
ip link set lo up
ip link add br-throw type bridge
ip link set ens3 master br-throw up
ip link set br-throw up

sysctl -w kernel.yama.ptrace_scope=0 kernel.pid_max=4194304 kernel.dmesg_restrict=0

setfacl -m u:66000:r /throwaway_lib/configs/1.tar.gz || :
setfacl -m u:66010:r /throwaway_lib/configs/2.tar.gz || :
setfacl -m u:66020:r /throwaway_lib/configs/3.tar.gz || :
setfacl -m u:66000:r /throwaway_lib/configs/4.tar.gz || :
setfacl -m u:66010:r /throwaway_lib/configs/5.tar.gz || :

for x in 1 2 3 4 5; do
	if [ -f /throwaway_lib/configs/"$x".tar.gz ]; then
		python3 /throwaway_lib/start-throwaway.py /throwaway_lib/configs/"$x".json || :
	fi
done
exec /__autoserver__/ctrtool mini-init -n /static/sh -C /dev/ttyS0 -r 2 -s15 -a1 -s10 -a3 -s12 -a2
