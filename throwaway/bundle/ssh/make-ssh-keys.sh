#!/bin/sh

set -eu

for x in rsa ecdsa ed25519; do
	ssh-keygen -t "$x" -f "ssh_host_${x}_key" -N "" -C ""
done
