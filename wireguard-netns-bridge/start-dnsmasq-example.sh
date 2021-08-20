#!/bin/sh
set -eu
nsenter --net="$1" dnsmasq -C "$2"
