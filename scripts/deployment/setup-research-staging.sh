#!/bin/sh
# Inputs are temporary; ownership/cleanup receipts survive reboot on disk.
set -eu
test "$(id -u)" = 0
install -d -o root -g root -m 0755 /run/arena-research-tools
install -d -o root -g root -m 0700 /run/arena-research-tools/staging
install -d -o root -g root -m 0700 /srv/arena/releases/research-tool-receipts
if ! mountpoint -q /run/arena-research-tools/staging; then
    mount -t tmpfs -o size=128m,mode=0700,nodev,nosuid,noexec tmpfs /run/arena-research-tools/staging
fi
test "$(findmnt -n -o FSTYPE --mountpoint /run/arena-research-tools/staging)" = tmpfs
