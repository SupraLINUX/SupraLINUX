# Hosted Ubuntu 26.04 QEMU/KVM autopkgtest and milestone snapshots

This opt-in workflow builds a real Ubuntu 26.04 amd64 guest with the official
`autopkgtest-build-qemu` tool and Ubuntu archive signature keyring.
It runs a representative DEP-8 test inside QEMU with KVM acceleration.
It is triggered only by `ci:hosted-ubuntu-guest` on same-repository PRs
or manual dispatch, **never** as ordinary PR CI.

The initial guest construction (run 38693007782) failed before DEP-8 at
grub-pc/linux-image configuration: the builder propagated the runner-specific
TMPDIR into a chroot that lacked that path, then vmdb2/kpartx also failed
cleanup. That is INFRA_INVALID, not a package Attempt or image PASS.
The scoped repair removes this host-only environment variable from the
builder. Raw vmdb2 verbose logs are **not** uploaded because they may expose
the GitHub-hosted environment; only filtered diagnostics are retained.

The 8 GiB virtual qcow2 base is cache-only. A successful DEP-8 test seals the
snapshot with its SHA-256, builder script checksum, Ubuntu keyring checksum,
creation time, and exact authorizing commit. Cache restores reject wrong
content or input bytes, snapshots older than eight days and backing-chain
bases. Keyed by calendar week and input files, immutable cache entries are
regenerated on misses, and the next release campaign must rebuild from zero.
Pull-request cache scope limits reuse across unrelated PRs. This is a
performance optimization within the permitted cache namespace, **not** a
cross-campaign or independently archived image. Cross-campaign reuse requires
a separate authorized, SHA-256-indexed durable artifact store; do not assume
the GitHub cache provides it.
Each test runs in an isolated autopkgtest QEMU overlay and the unchanged base
is reused. GitHub's retention and eviction rules mean the cache is *not*
a durable artifact or release evidence archive.

The first hosted guest run (38693007782) failed at vmdb2/grub because the
builder passed a host-only TMPDIR into the chroot. The second run (38695358122)
built and booted Ubuntu 26.04 successfully under hosted KVM and updated APT,
but its generated DEP-8 source tree omitted debian/changelog, so autopkgtest
rejected it before running guest-smoke. Neither run sealed or saved a snapshot.
After these two infrastructure-invalid outcomes, the fixture is retained as
real, complete, versioned source files and validated with dpkg-parsechangelog
in cheap Repository Policy before any further hosted VM experiment.

The smoke checks the guest's Ubuntu 26.04 identity, architecture, Python
runtime and Ubuntu archive keyring. A PASS certifies this **mechanism only**:
it does not authorize KDE package Attempts, change the frozen Plasma 6.7.5
stack, replace the physical authoritative runner, or certify Ubuntu/Qt ABI.
No persistent VMs or host network changes occur on the user's computer.

Official references:
- https://manpages.ubuntu.com/manpages/resolute/man1/autopkgtest-build-qemu.1.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
