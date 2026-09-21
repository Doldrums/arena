#!/bin/sh
# Explicit operator provisioning only; never invoked by validation or PR checks.
set -eu
umask 027
getent passwd arena >/dev/null || useradd --system --create-home --home-dir /srv/arena --shell /usr/sbin/nologin arena
getent passwd arena-provider >/dev/null || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin arena-provider
chown root:root /srv/arena
chmod 0755 /srv/arena
install -d -m 0755 /opt/arena /opt/arena/releases /opt/arena-python
install -d -m 0700 -o arena -g arena /srv/arena/control /srv/arena/runs /srv/arena/configs
install -d -m 0755 /srv/arena/sources /srv/arena/envs /srv/arena/tasks
install -d -m 0711 /etc/arena
install -d -m 0750 -o root -g arena-provider /etc/arena/provider
UV_PYTHON_INSTALL_DIR=/opt/arena-python uv python install 3.11
UV_PYTHON_INSTALL_DIR=/opt/arena-python uv venv --python 3.11 /opt/arena/venv
chmod -R a+rX /opt/arena-python /opt/arena/venv
