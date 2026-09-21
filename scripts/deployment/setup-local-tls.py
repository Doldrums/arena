#!/usr/bin/env python3
"""Provision only the local relay identity and public worker trust bundle.

Requires root on the private Linux worker. Does not install/restart a service,
read any model credential, or send an inference request. Existing CA identities
are reused; an incomplete existing identity fails closed for operator review.
"""
import grp
import os
from pathlib import Path
import pwd
import subprocess


def openssl(*args):
    subprocess.run(["openssl", *map(str, args)], check=True, capture_output=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Root is required to provision the private CA")
    os.umask(0o077)
    try:
        pwd.getpwnam("arena-relay")
    except KeyError:
        subprocess.run(["useradd", "--system", "--no-create-home", "--home-dir", "/nonexistent",
                        "--shell", "/usr/sbin/nologin", "arena-relay"], check=True)
    group = grp.getgrnam("arena-relay").gr_gid
    ca = Path("/etc/arena/local-ca")
    server = Path("/etc/arena/local-tls")
    for path, mode in ((ca, 0o700), (server, 0o750)):
        if path.is_symlink():
            raise SystemExit("Refusing a symlink certificate directory")
        path.mkdir(mode=mode, parents=True, exist_ok=True)
        path.chmod(mode)
    os.chown(server, 0, group)
    ca_files = (ca / "ca.key", ca / "ca.pem")
    if any(p.exists() for p in ca_files) and not all(p.is_file() and not p.is_symlink() for p in ca_files):
        raise SystemExit("Incomplete or unsafe existing CA identity")
    if not all(p.exists() for p in ca_files):
        openssl("req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256", "-days", "365",
                "-subj", "/CN=Arena private worker loopback CA", "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-keyout", ca_files[0], "-out", ca_files[1])
    leaf_files = (server / "server.key", server / "server.pem")
    if any(p.exists() for p in leaf_files) and not all(p.is_file() and not p.is_symlink() for p in leaf_files):
        raise SystemExit("Incomplete or unsafe existing relay identity")
    if not all(p.exists() for p in leaf_files):
        csr = server / "server.csr"
        ext = server / "extensions.cnf"
        ext.write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\n"
                       "keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n")
        openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost",
                "-keyout", leaf_files[0], "-out", csr)
        openssl("x509", "-req", "-in", csr, "-CA", ca_files[1], "-CAkey", ca_files[0],
                "-CAcreateserial", "-out", leaf_files[1], "-days", "90", "-sha256", "-extfile", ext)
        csr.unlink()
        ext.unlink()
    for path in ca_files:
        path.chmod(0o600)
        os.chown(path, 0, 0)
    for path in leaf_files:
        path.chmod(0o640)
        os.chown(path, 0, group)
    openssl("verify", "-CAfile", ca_files[1], "-verify_hostname", "localhost", leaf_files[1])
    openssl("x509", "-checkend", "86400", "-noout", "-in", leaf_files[1])
    bundle = Path("/etc/ssl/certs/arena-worker-bundle.pem")
    if bundle.is_symlink():
        raise SystemExit("Refusing a symlink public bundle")
    public = Path("/etc/ssl/certs/ca-certificates.crt").read_bytes() + b"\n" + ca_files[1].read_bytes()
    temporary = bundle.with_suffix(".new")
    with temporary.open("xb") as stream:
        stream.write(public)
    temporary.chmod(0o644)
    temporary.replace(bundle)
    print("Local CA and relay identity prepared; public bundle:", bundle)


if __name__ == "__main__":
    main()
