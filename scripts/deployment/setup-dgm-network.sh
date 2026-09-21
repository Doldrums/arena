#!/bin/sh
# Explicit operator deployment only. Never called by validation or tests.
# Quiesce DGM before changing its dedicated bridge/host firewall.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root is required' >&2; exit 1; }
running=$(docker ps --filter label=arena.dgm-proxy=dgm-prebuilt-v1 --format '{{.ID}}')
[ -z "$running" ] || { echo 'DGM containers are active; leave their network unchanged' >&2; exit 1; }
if ! docker network inspect arena-dgm-internal >/dev/null 2>&1; then
    docker network create --driver bridge --internal \
        --subnet 172.30.88.0/24 --gateway 172.30.88.1 \
        --opt com.docker.network.bridge.name=br-arena-dgm \
        --opt com.docker.network.bridge.enable_icc=false arena-dgm-internal
fi
iptables-restore --wait --noflush <<'RULES'
*filter
:ARENA_DGM_HOST - [0:0]
-F ARENA_DGM_HOST
-A ARENA_DGM_HOST -d 172.30.88.1/32 -p tcp -m tcp --dport 8789 -j ACCEPT
-A ARENA_DGM_HOST -j DROP
COMMIT
RULES
while iptables -w -C INPUT -i br-arena-dgm -j ARENA_DGM_HOST 2>/dev/null; do
    iptables -w -D INPUT -i br-arena-dgm -j ARENA_DGM_HOST
done
iptables -w -I INPUT 1 -i br-arena-dgm -j ARENA_DGM_HOST
docker network inspect --format '{{.Id}}' arena-dgm-internal
