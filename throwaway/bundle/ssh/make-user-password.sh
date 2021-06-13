#!/bin/sh
set -eu
printf 'Enter username (should match username in config json): '
read -r TB_USERNAME

umask 077
printf '%s:' "$TB_USERNAME" > passwords

openssl passwd -6 >> passwords
