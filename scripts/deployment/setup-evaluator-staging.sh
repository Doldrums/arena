#!/bin/sh
# Host-visible, bounded storage: Docker must see the same tmpfs as the broker.
set -eu
test "$(id -u)" = 0
install -d -o root -g root -m 0755 /run/arena-evaluator
install -d -o root -g root -m 0700 /run/arena-evaluator/staging
if ! mountpoint -q /run/arena-evaluator/staging; then
    mount -t tmpfs -o size=128m,mode=0700,nodev,nosuid,noexec tmpfs /run/arena-evaluator/staging
fi
test "$(findmnt -n -o FSTYPE --mountpoint /run/arena-evaluator/staging)" = tmpfs
