#!/bin/sh
set -eu
base=/sys/fs/cgroup/arena-workers
mkdir -p "$base"
printf '+cpu +memory +pids' > "$base/cgroup.subtree_control"
printf '9600000 100000' > "$base/cpu.max"
printf '322122547200' > "$base/memory.max"
printf '0' > "$base/memory.swap.max"
mkdir -p "$base/supervisor"
chown arena:arena "$base" "$base/cgroup.procs" "$base/cgroup.subtree_control"
chown arena:arena "$base/supervisor" "$base/supervisor/cgroup.procs"
chmod 0750 "$base"
