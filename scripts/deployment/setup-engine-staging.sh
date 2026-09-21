#!/bin/sh
# Shared host mount: the Docker daemon must see the same staged files.
set -eu
test "$(id -u)" = 0
install -d -o root -g root -m 0755 /run/arena-engine
install -d -o root -g root -m 0700 /run/arena-engine/staging /run/arena-engine/registrations
if ! mountpoint -q /run/arena-engine/staging; then
    mount -t tmpfs -o size=1g,mode=0700,nodev,nosuid,noexec tmpfs /run/arena-engine/staging
fi
test "$(findmnt -n -o FSTYPE --mountpoint /run/arena-engine/staging)" = tmpfs
install -d -o root -g root -m 0755 /run/arena-evaluator-engine
install -d -o root -g root -m 0700 /run/arena-evaluator-engine/staging
if ! mountpoint -q /run/arena-evaluator-engine/staging; then
    mount -t tmpfs -o size=128m,mode=0700,nodev,nosuid,noexec tmpfs /run/arena-evaluator-engine/staging
fi
test "$(findmnt -n -o FSTYPE --mountpoint /run/arena-evaluator-engine/staging)" = tmpfs
