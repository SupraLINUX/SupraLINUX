# Authoritative Plasma package builds

`manifests/kde-plasma-package-build.json` records each individually reviewed
packaging overlay, its exact input hashes, binary identities and current scope.
The reusable preparation/build scripts consume that contract. The controlled
`ci:plasma-package-build` label starts one reviewed node on one disposable JIT
runner. Ordinary PR CI validates the contract without reopening materialization.

The initial node is Breeze GRUB 6.7.5. Its resources require only debhelper to
package, so this sample uses the certified clean golden image. It does not need
the Frameworks milestone or a Qt transition. Ocean, Oxygen and KDecoration have
also closed authoritative package PASS. Wallpapers are individually admitted;
remaining nodes stay locked until their own review. KDecoration now enables the
upstream tests that Ubuntu's reference rules suppressed.

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

The captured Ubuntu
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
passed to sbuild. Every build uses a disposable Ubuntu buildd environment with
updates and security enabled. Reviewed nodes may derive its tarball from the
immutable bare milestone base: verify the contracted SHA, Ubuntu identity and
absence of Frameworks/Qt SDK packages, replace only APT sources, then require
`--apt-update --apt-distupgrade` for both the infrastructure probe and candidate
build. These options refresh and upgrade each disposable environment, as defined
in the [sbuild manual](https://manpages.debian.org/testing/sbuild/sbuild.1.en.html).
The original cached tarball is unchanged. Admission records base and derived
hashes, the Ubuntu archive keyring, all installed base packages, suites and time.
Fresh mmdebstrap remains the default for records without this explicit policy.

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

Oxygen Attempt 2 built successfully with the explicit Qt 6 selector. Lintian
rejected an embedded LGPL-3 text without its common-license reference. The
original FAIL is retained; packaging now refers to
`/usr/share/common-licenses/LGPL-3`, preserving the SPDX terms and attributions.

Oxygen Attempt 3 reached sbuild PASS and lintian PASS. A host DNS failure while
monitoring GitHub triggered controller cleanup during autopkgtest setup. No
test completed, no original guest result was written and no Actions artifact
was uploaded. The sealed host copy preserves the complete candidate source,
binary, changes/buildinfo and available logs. Its explicit interruption
observation is INFRA_INVALID and cannot admit the binary downstream. Read-only
GitHub API transport now retries transient failures with a finite budget,
buffering each response; mutations and JIT creation remain single-shot.

## Compiled-library package testing

The generic runner supports a reviewed `baseline_setup_script` inside the
packaging test directory. Its digest belongs to the frozen packaging contract.
The setup compiles and executes a client using Ubuntu packages before candidate
binaries or retained Frameworks inputs are installed. Package autopkgtests can
then exercise that same binary after the upgrade and retain it as a test artifact.
Selected predecessor binaries are also supplied to autopkgtest with exact
identities, keeping build and runtime input scopes coherent.

`upstream_tests` lists substantive CTest entries expected during sbuild. The
runner rejects missing or failed entries and an incomplete suite. Closure
preserves the exact test result separately from the build and installed-package
tests. KDecoration is the first prepared compiled Plasma library using this
contract; its execution requires individual manifest admission.

Oxygen Attempt 4 closed PASS on the authoritative KVM lane: both sound resource
and Ubuntu-upgrade tests passed. Sources, binary, changes/buildinfo, logs and
cache-probe evidence were retained, and empty-cache offline restoration passed.
KDecoration is now individually admitted with three enabled upstream tests and
a compiled Ubuntu client exercised before and after candidate installation.

KDecoration Attempt 1 passed sbuild, retained Ubuntu symbol guards and all
four actual CTest entries (three source tests plus ECM's `appstreamtest`).
The verifier incorrectly assumed exactly three entries. Its original runner
FAIL remains immutable; a separate diagnosis classifies the false negative as
INFRA_INVALID. The corrected verifier requires every declared test and matches
the success summary to every executed entry, rejecting failed or missing tests.
The failed artifact retains sources and logs but lacks candidate binaries:
verification ran before capture. The runner now captures binary, changes,
buildinfo and debug outputs immediately after sbuild, before later verification.

KDecoration Attempt 2 closed PASS in
[run 37249338022](https://github.com/SupraLINUX/SupraLINUX/actions/runs/37249338022):
four upstream tests, unchanged Ubuntu client execution after upgrading both
libraries, a client compiled against the new headers, symbol/SONAME guards,
lintian and APT checks. Five binary/debug payloads and complete source/buildinfo
closure are retained and restored offline. Actions omitted two generated hidden
CMake files from the client build directory. Both were recovered byte-for-byte
from the independently sealed guest copy and retained in a hashed supplement;
the original result and Actions ZIP remain unchanged. The export recovery proof
is immutable. The workflow now includes hidden files, and recovery rejects
altered bytes, unsealed files and ordinary missing files.

Wallpapers preserve epoch 4, the Ubuntu binary name and Architecture all. Tests
cover 37 wallpaper sets, 288 resources, 143 safe aliases and decoding of 108
unique images. This is the additional collection; the default wallpaper belongs
to Breeze and later desktop integration.

Wallpaper Attempt 1 built and passed lintian, but the installed resource tests
rejected two normalized ImageMagick timestamp text fields in Shell's screenshot.
The original FAIL and entire artifact remain retained. The diagnosis verifies
unchanged compressed pixels, EXIF and other chunks. The corrected test validates
CRC and timestamp syntax and normalizes only `date:create`/`date:modify` values,
preserving their keys/order and all other text. Regressions reject pixel or author
changes, malformed dates and CRC corruption. All 37 sets/288 resources/108 images
in the real retained installed payload pass the repaired local verifier; the
authoritative rerun remains required.

Future successful exports compact byte-identical `.deb`/`.ddeb` copies retained
by autopkgtest. A receipt records their original path, canonical path, digest and
size. Canonical sources/binaries/buildinfo, clients and logs remain retained;
distinct or unrelated payloads are never removed. This avoids transporting a
second large wallpaper binary while preserving the complete package closure.

Wallpaper Attempt 2 completed package PASS on KVM in run 37252562053: both
installed tests passed, including all 108 image decodes and the Ubuntu upgrade.
The host exhausted GitHub DNS retries after package execution, interrupting the
Actions export. The workflow failed; its package step succeeded. No Actions
artifact exists. Closure therefore uses the complete independently sealed guest
payload and original job/host metadata: a source-complete local ZIP is retained
by its own digest with `artifact_id: null` and origin `sealed-host-package-export`.
Every original result hash, source/binary/buildinfo/changes identity, test result
and empty-cache offline restore passed. The host exit 28 and workflow/export
failure remain recorded separately; they are not rewritten as success.

The active-job monitor now checks the guest process when API reads fail and
keeps the working VM alive until the process exits or the job deadline expires.
Its bounded synthetic read-fault option supports a small runner-contract probe
before subsequent package execution. This changes monitoring, not package tests.

The live read-outage probe passed on source `8fe666d45718d429ca47b321ea2b7ef258ab6182`
in runner-contract run 37255396918/job 111591237798. One injected monitor read
failure was followed by a local QGA observation with `exited: false`; the guest
remained alive and completed the workflow successfully. The independently sealed
host bundle and exact monitor/test input hashes are retained in
`manifests/evidence/plasma/infrastructure/monitor-read-recovery-20261005/`.
This is an infrastructure certification and consumes no package Attempt.

Breeze Plymouth Attempt 1 built successfully and passed lintian and the installed
resource test (89 resources/84 image decodes), but the Ubuntu baseline setup did
not execute. The QEMU serial backend silently truncated an inline base64 line
above the Linux canonical terminal limit: the setup shell returned zero while
its script was empty. The original FAIL, sources/binaries/debug outputs and test
logs remain immutable. A separate diagnosis records INFRA_INVALID and incomplete
ABI/consumer scope; no candidate is admitted downstream. A real local canonical
PTY reproduced this exact zero-status/missing-script behavior. The repair wraps
base64 at 76 columns and verifies SHA-256 inside the guest before execution;
regressions prove a large script survives the terminal and corruption is rejected.
The small runner-contract transport probe must pass before the package rerun.
The consumer's Plymouth pkg-config SDK also explicitly requires Ubuntu's
libevdev-dev, libxkbcommon-dev and libudev-dev; these are declared for compilation.

Individual source review also found an external provider version gap:
KWayland 6.7.5 requires Plasma Wayland Protocols >=1.21.0, while the Ubuntu
reference exposes 1.20.0-2. Historical provider availability evidence does not
certify changed upstream minimums. The live supplementary-provider manifest
records signed KDE stable 1.22.0 as a preparation candidate, with package and
protocol compatibility gates pending. This adds an external build provider;
it does not change the pinned Plasma release or replace Qt/Wayland runtime.

The first live transport probe (run 37292037424) decoded all 45,109 setup bytes
and matched SHA-256. Its harness then failed source extraction because it provided
Debian/control without a changelog. The original INFRA_INVALID probe remains
sealed and archived; no package Attempt was consumed. The harness now uses the
explicit tests-only built-tree supported by Ubuntu autopkgtest. Its classification
was verified with the actual 5.55 parser before repeating the small KVM probe.

The corrected transport certification passed in nested KVM on source
`4e8607346dea9f2596871bba9051eacac0c4a13b`, run 37292928896/job 111707360642.
All 45,109 script bytes matched SHA-256 in the guest and the preserved-setup test
passed. The original result, job/host metadata and independently retained complete
payload are bound under `infrastructure/baseline-transport-probe2-20261005/`.
Its exact generator/probe/QEMU-wrapper hashes are checked for applicability.
This is an infrastructure PASS, separate from Plymouth package Attempt 2.

Plymouth Attempt 2 preserved its original INFRA_INVALID result (run 37293399191):
sbuild and lintian passed, but the Ubuntu SDK client failed during testbed setup
because gcc did not install its recommended C headers with no-install-recommends.
The setup and consumer now explicitly declare build-essential. The reusable
reviewed Ubuntu baseline preflight executes the exact frozen setup/client in a
nested KVM testbed before another candidate build, without consuming an Attempt.
Its PASS only certifies that baseline; it does not certify candidate compatibility.

The exact corrected Plymouth Ubuntu baseline passed nested KVM on source
`4164b993318158218843a5d88359ff0ea3dfbadd`, run 37295330128/job 111715082081.
Its compiler, SDK dependencies and actual Ubuntu plugin lifecycle client executed
successfully in all three modes. The complete original preflight payload, host
seal and relevant input hashes are retained independently of Actions expiry.
Candidate package compilation and upgrade compatibility remain separate gates.

For newly admitted packages with a reviewed Ubuntu client, the authoritative
runner now executes that baseline before preparing sbuild. It retains the result
inside the package evidence bundle. A setup failure therefore consumes no package
Attempt and stops before compilation. New records can require this preflight;
closure validates its exact client hash, source/run identity and nested KVM PASS.
The historical package attempts retain their original execution order and scope.

Breeze Plymouth 6.7.5-0supralinux1 Attempt 3 closed PASS on source
`4164b993318158218843a5d88359ff0ea3dfbadd`, run 37295892875/job 111716893450.
Clean sbuild, lintian, 89 resources/84 image decodes, the unchanged Ubuntu client
running after candidate upgrade and the rebuilt consumer passed in nested KVM.
The original Actions ZIP SHA-256 is
`02ef7f78c6aa18c316130c142e0edf03b26658e15b07d18c14e324ff1b379d62`;
source, binary/debug packages, buildinfo, changes, clients and logs are retained
with verified empty-cache offline restoration. Full initramfs/boot remains an ISO
integration gate. The earlier infrastructure failures retain their original scope.
