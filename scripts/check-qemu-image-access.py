#!/usr/bin/env python3
"""Check POSIX access ACLs for the libvirt QEMU identity without requiring sudo."""
import argparse
import os
import pwd
import subprocess
from pathlib import Path


def permissions(acl, owner, group, uid, groups):
    if uid == owner:
        return set(acl[("user", "")])
    mask = set(acl.get(("mask", ""), "rwx"))
    if ("user", str(uid)) in acl:
        return set(acl[("user", str(uid))]) & mask
    matches = []
    if group in groups:
        matches.append(acl[("group", "")])
    matches.extend(value for (kind, identity), value in acl.items()
                   if kind == "group" and identity and int(identity) in groups)
    if matches:
        return set("".join(matches)) & mask
    return set(acl[("other", "")])


def check(image, user):
    identity = pwd.getpwnam(user)
    assert identity.pw_uid != 0, "Authoritative QEMU must not run as root"
    groups = set(os.getgrouplist(user, identity.pw_gid))
    image = image.resolve(strict=True)
    assert image.is_file(), "Backing image must be a regular file"
    for path, required in [(parent, "x") for parent in reversed(image.parents)] + [(image, "r")]:
        status = path.stat()
        output = subprocess.check_output(["getfacl", "-c", "-p", "-n", "-E", str(path)], text=True)
        acl = {}
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) == 3 and parts[0] in {"user", "group", "mask", "other"}:
                acl[(parts[0], parts[1])] = parts[2]
        assert required in permissions(acl, status.st_uid, status.st_gid, identity.pw_uid, groups), \
            f"QEMU user {user} lacks {required} permission on {path}"
    print(f"QEMU backing image POSIX ACL access: PASS; user={user}; image={image}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--user", default="libvirt-qemu")
    args = parser.parse_args()
    check(args.image, args.user)
