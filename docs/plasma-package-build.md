# Authoritative Plasma package builds

`manifests/kde-plasma-package-build.json` records each individually reviewed
packaging overlay, its exact input hashes, binary identities and current scope.
The reusable preparation/build scripts consume that contract. The controlled
`ci:plasma-package-build` label starts one reviewed node on one disposable JIT
runner. Ordinary PR CI validates the contract without reopening materialization.

The initial node is Breeze GRUB 6.7.5. Its resources require only debhelper to
package, so this sample uses the certified clean golden image. It does not need
the Frameworks milestone or a Qt transition. Ocean Sound Theme is the next individually reviewed node. The remaining
nodes stay locked until their own review. For example, KDecoration's Ubuntu rules
currently suppress `dh_auto_test`; that requires review before its admission.

The runner rechecks KDE's detached signature and frozen source/packaging hashes,
creates a source package, builds in a fresh resolute sbuild/unshare rootfs with
updates/security enabled, checks binary version/architecture, runs lintian and
runs substantive autopkgtests in nested QEMU with KVM required. The testbed first
installs Ubuntu's current package; APT then upgrades it to the candidate. Tests
check all installed resources against signed upstream, PNG/font structure,
image/font references, version precedence and APT dependency consistency.
PNG CRCs and all content/rendering chunks remain exact; only the `tIME` timestamp
may change through Debian's reproducibility normalization. Other resources keep
their exact upstream byte hashes.

This gate does not certify graphical GRUB rendering, theme activation, the whole
Plasma stack or a release. Breeze GRUB only installs resources; selecting the
default boot theme belongs to later distro integration. A PASS must retain the
source, binaries, `.changes`, `.buildinfo`, logs and result independently of
Actions expiry before admitting the evidence. Failed infrastructure remains
separate from package/test failure. Final merge/publication require their gates.

## First package closure

Breeze GRUB `6.7.5-0supralinux1` passed clean sbuild, lintian and both
autopkgtests on the authoritative KVM runner in
[run 37232072978](https://github.com/SupraLINUX/SupraLINUX/actions/runs/37232072978).
APT upgraded Ubuntu's `6.6.4-0ubuntu1` package without removing packages. The
artifact, complete source closure, binaries, buildinfo, changes and logs are
retained locally by digest; restoration from an empty cache passed without
GitHub. The archive contains one unique binary package plus the identical copy
used by autopkgtest. Off-host backup has not been verified.

The earlier runner variable collision remains `INFRA_INVALID`; the strict PNG
timestamp comparison remains `FAIL`. Their original evidence and artifacts are
preserved. Neither result was rewritten as PASS. The final package contract
records all three Attempts and binds the PASS to its exact source commit,
workflow/job, packaging hashes and host evidence seal.

The other 33 Level 0 nodes still require individual review. The captured Ubuntu
reference inventory in `manifests/evidence/plasma/level0-packaging-inventory.json`
lists 13 test-step overrides and no autopkgtest control files; it is advisory
inventory and does not admit any package.

## Frameworks cache consumption

The host still admits the certified Ubuntu golden image and checks its current
input digest. For reviewed Plasma packages requiring Frameworks, it separately
admits the Frameworks milestone by image SHA, provenance, current artifact plan
and qemu-img check, then uses that cache as the disposable overlay backing image.
The cache is never represented as the golden image or as final package evidence.

Inside the guest, every cached binary and the APT index are hash-verified;
selected predecessor package/source/version/architecture must match the reviewed
contract and current eligible Frameworks node. Only those explicit binaries are
passed to sbuild. Every package uses a new Ubuntu buildd rootfs with updates and
security enabled. The milestone rootfs is not reused because its older mirror
state must not define the current build environment.

An infrastructure-only ECM/Qt consumer must pass in sbuild before a Plasma
Attempt starts. It retains source, binary, buildinfo, changes and logs, and checks
the exact ECM version in buildinfo. A cache/probe failure consumes no Plasma
Attempt. Ocean's package tests compare every installed resource with signed
upstream and decode every audio stream; actual desktop playback remains a session
gate. Ubuntu Qt is reused; no Qt substitution is introduced.

The first milestone-backed VM creation failed before a workflow or package
started: the backing directory mode did not permit the QEMU identity to traverse
it. Its original host evidence is retained as an infrastructure incident with no
package Attempt. The builder now grants a narrow named-user ACL on the milestone
directory, and orchestration checks effective POSIX ACL permissions before VM
creation. This check is read-only and does not require sudo authentication.

## Sound theme closure and artifact roles

Ocean Sound Theme `6.7.5-0supralinux1` passed authoritative sbuild, lintian,
resource integrity/audio decoding and an Ubuntu APT upgrade in
[run 37242861863](https://github.com/SupraLINUX/SupraLINUX/actions/runs/37242861863).
All 64 regular resources and 14 aliases were retained. The ECM/Qt infrastructure
consumer passed before the Ocean Attempt. This is package/resource evidence;
actual PipeWire playback still requires session integration.

The complete ZIP is retained by digest, including the infrastructure consumer and
autopkgtest evidence. Its plan declares `packages/` as the canonical package
payload. Retention verifies only that source-scoped `.dsc`, `.changes`,
`.buildinfo` and binary closure for downstream admission; the synthetic consumer
cannot enter the desktop package pool. Five regression checks reject an
ambiguous artifact, a wrong source scope, altered source bytes and unsafe paths.
The generic closure tool verifies test results, source commit, host evidence seal
and restoration from an empty cache before recording a package PASS.

Oxygen Sound Theme is reviewed next, preserving epoch 4, Multi-Arch foreign and
all 50 legacy KF5 sound aliases. Its obsolete Ubuntu configure switch is replaced
by upstream's actual `KF5_SUPPORT=ON` option. Tests verify every dpkg-owned sound
resource and decode both current and legacy streams. No Qt replacement or
upstream behavior patch is introduced.

Orchestration now takes the golden image hash from its successful canonical
admission record, avoiding a second full-image hash pass. Each image is still
verified against its immutable provenance and current input digest. Compiled
package capture also preserves `.ddeb` files; the first infrastructure consumer's
missing debug payload remains outside the canonical Ocean source/binary closure.

Oxygen Attempt 1 failed in CMake configuration: its legacy ECM minimum selects
Qt 5 unless the major version is specified. The original valid package FAIL and
source artifact are retained. The repair explicitly sets `QT_MAJOR_VERSION=6`
while keeping `KF5_SUPPORT=ON`. The original `sbuild_result=not-run` placeholder
is preserved as a runner-marker defect; future executions set FAIL before sbuild
and PASS only after success. The failure recorder keeps source checksum closure
and the entire ZIP while prohibiting downstream admission.
