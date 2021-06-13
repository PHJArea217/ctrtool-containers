#!/bin/sh

set -eu

mount -t squashfs -o ro,nosuid,nodev \
	"${THROWAWAY_MODULE_FILE:=/boot_disk/extra_container_modules/mix_4_amd64.sqf}" \
	"${THROWAWAY_MOUNT_PATH:=/container_images/ctr_fs4}"

ip link set lo up
ip link add br-throw type bridge
# ip link set ens3 master br-throw up
ip link set br-throw up

sysctl -w kernel.yama.ptrace_scope=0
