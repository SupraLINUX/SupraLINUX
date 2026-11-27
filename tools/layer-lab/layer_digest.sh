#!/usr/bin/env bash
# Deterministic logical tree digest; not a physical disk-image hash.
# Preserve contents, paths, ownership, modes, mtime, link topology, ACLs
# and extended attributes. Access/change timestamps intentionally excluded.
layer_digest() (
    set -euo pipefail
    export LC_ALL=C
    unset TAR_OPTIONS POSIXLY_CORRECT
    tar --format=posix --sort=name --numeric-owner --acls --xattrs \
        --xattrs-include='*' --one-file-system \
        --pax-option='exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime' \
        -cpf - -C "$1" . | sha256sum
)
