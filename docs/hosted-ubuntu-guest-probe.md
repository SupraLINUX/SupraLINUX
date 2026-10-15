# Hosted Ubuntu 26.04 QEMU/KVM autopkgtest and milestone snapshots

This opt-in workflow builds a real Ubuntu 26.04 amd64 guest with the official
`autopkgtest-build-qemu` tool and Ubuntu archive signature keyring.
It runs a representative DEP-8 test inside QEMU with KVM acceleration.
It is triggered only by `ci:hosted-ubuntu-guest` on same-repository PRs
or manual dispatch, **never** as ordinary PR CI.

The 8 GiB virtual qcow2 base is cache-only. A successful DEP-8 test seals the
snapshot with its SHA-256, builder script checksum, Ubuntu keyring checksum,
creation time, and exact authorizing commit. Cache restores reject wrong
content or input bytes, snapshots older than eight days and backing-chain
bases. Keyed by calendar week and input files, immutable cache entries are
regenerated on misses, and the next release campaign must rebuild from zero.
Each test runs in an isolated autopkgtest QEMU overlay and the unchanged base
is reused. GitHub's retention and eviction rules mean the cache is *not*
a durable artifact or release evidence archive.

The smoke checks the guest's Ubuntu 26.04 identity, architecture, Python
runtime and Ubuntu archive keyring. A PASS certifies this **mechanism only**:
it does not authorize KDE package Attempts, change the frozen Plasma 6.7.5
stack, replace the physical authoritative runner, or certify Ubuntu/Qt ABI.
No persistent VMs or host network changes occur on the user's computer.

Official references:
- https://manpages.ubuntu.com/manpages/resolute/man1/autopkgtest-build-qemu.1.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
