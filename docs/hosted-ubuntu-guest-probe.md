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

## Verified hosted guest mechanism milestone (2026-10-15)

The exact checkout `1e814f7c321a6749e3156a76cf6a1db813f99353`
produced two independent **PASS** executions:

- Run **38696340689** (Ubuntu hosted runner image `20260927.149.1`):
  clean Ubuntu 26.04 guest construction, actual QEMU/KVM guest boot, DEP-8
  `guest-smoke PASS`, immutable base snapshot sealing and successful Actions
  cache save. Diagnostic artifact `11954261425`.
- Run **38697145580** (hosted runner image `20261012.163.1`):
  exact cache hit, SHA-256 admission of the restored independent image, real
  guest DEP-8 `guest-smoke PASS` again, **without** rebuilding the base.
  Restored cache upload size: 1,318,909,194 bytes. Diagnostic artifact
  `11954946582`.

Both runs produced the same DEP-8 summary digest:
`8aa5951ad5bd0b763cb76c6f5a283d5fe16f6e2f4540de19d18ff4fe1f871774`.
The cache key and execution identities are indexed at
`manifests/evidence/hosted-ubuntu-guest-milestone-2026-10-15.json`.
The full base-image SHA-256 lives inside the sealed cached `snapshot.json`,
which is rechecked during restore; **it has not been separately exported
to a durable archive**. GitHub cache remains an evictable accelerator, and
its PR/branch scope prevents treating it as cross-campaign release storage.

These PASS results certify **this hosted Ubuntu KVM/DEP-8 mechanism**, not
any package, ABI or KDE/Qt release gate. The next stage is separate
hosted-runner parity verification of clean sbuild, installed Ubuntu clients,
source/package identity, independent artifact retention and reproducible
input selection before any authority migration.

## Next mechanism: clean sbuild inside the cached hosted Ubuntu KVM guest

The same DEP-8 fixture invokes `clean-sbuild-smoke` **within the original
guest-smoke test session**: construct a small native Debian source, create an
independent signed-Ubuntu buildd tarball and run
`sbuild --chroot-mode=unshare` with that exact rootfs.
Verify the resulting `.deb`, `.changes` and `.buildinfo` identity.
Do not inject any KDE SDKs. Dispose of the inner buildd rootfs after testing.
The base Ubuntu QEMU milestone is unchanged and can be restored as before.

The first extension attempt (GitHub run 38700751372, commit 81dc499)
restored the correct snapshot and passed the original `guest-smoke`. Before
the separate `clean-sbuild-smoke` could start, however, autopkgtest attempted
to relaunch QEMU for the next test, which failed to reopen /dev/kvm with
`Permission denied`. The result is INFRA_INVALID for the extended
mechanism; no sbuild build started and no KDE Attempt was consumed.
A single DEP-8 test now performs both checks without that inter-test relaunch.
The eventual result must be assessed independently, with the original failure
retained.

The extended mechanism is **not yet certified until it passes in hosted KVM**.
Its eventual PASS must not promote KDE CLI Tools, any official Ubuntu client
compatibility gate or release-relevant package certification automatically.
This adds no new workflow or per-package runner.

The smoke checks the guest's Ubuntu 26.04 identity, architecture, Python
runtime and Ubuntu archive keyring. A PASS certifies this **mechanism only**:
it does not authorize KDE package Attempts, change the frozen Plasma 6.7.5
stack, replace the physical authoritative runner, or certify Ubuntu/Qt ABI.
No persistent VMs or host network changes occur on the user's computer.

Official references:
- https://manpages.ubuntu.com/manpages/resolute/man1/autopkgtest-build-qemu.1.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
