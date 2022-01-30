#!/bin/sh
set -eu
umask 077

tar -cC bundle-1 --owner=0 --group=0 . | gzip -9c > throwaway_lib/configs/1.tar.gz
tar -cC bundle-2 --owner=0 --group=0 . | gzip -9c > throwaway_lib/configs/2.tar.gz
tar -cC bundle-3 --owner=0 --group=0 . | gzip -9c > throwaway_lib/configs/3.tar.gz
rm -f throwaway_lib/configs/4.tar.gz throwaway_lib/configs/5.tar.gz

tar -c throwaway_lib scripts --owner=0 --group=0 > root_modules/throwaway.tar
sha256sum root_modules/throwaway.tar | head -c 64 > root_modules/throwaway.manifest
find root_modules -print0 | cpio -0o -H newc -R 0:0 | xz -e --check=crc32 | cat /boot_disk/as_boot/initrd.xz - > throwaway_initramfs.xz

tar -cC bundle-4 --owner=0 --group=0 . | gzip -9c > throwaway_lib/configs/4.tar.gz
tar -cC bundle-5 --owner=0 --group=0 . | gzip -9c > throwaway_lib/configs/5.tar.gz
rm -f throwaway_lib/configs/1.tar.gz throwaway_lib/configs/2.tar.gz throwaway_lib/configs/3.tar.gz

tar -c throwaway_lib scripts --owner=0 --group=0 > root_modules/throwaway.tar
sha256sum root_modules/throwaway.tar | head -c 64 > root_modules/throwaway.manifest
find root_modules -print0 | cpio -0o -H newc -R 0:0 | xz -e --check=crc32 | cat /boot_disk/as_boot/initrd.xz - > throwaway_2_initramfs.xz
