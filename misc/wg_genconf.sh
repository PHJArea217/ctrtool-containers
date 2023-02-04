#!/bin/bash
set -eu
printf '[Interface]\nPrivateKey='
wg genkey
printf 'ListenPort=%d\n\n[Peer]\nPublicKey=\nAllowedIPs=0.0.0.0/0,::/0\nEndpoint=\nPersistentKeepalive=25\n' "$((RANDOM%4000+12000))"
