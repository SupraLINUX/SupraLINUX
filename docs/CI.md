# SupraLINUX CI — Aurora validation

SupraLINUX CI validates packaging, clean-system composition and real VM behavior against Ubuntu 26.04 LTS (`resolute`), the base generation used by Aurora.

Current architecture state: **KDE Stack Qualification active; KSQ-0 CERTIFIED; KSQ-1 ACTIVE; C4 feature certification paused**. The C1-C3/C4.0/C4.1a results described below were produced by the historical Ubuntu KDE 6.6.6 / Frameworks 6.24 baseline and remain version-scoped evidence.

## Runner

Workflows use GitHub's `ubuntu-26.04` x64 runner. While that runner image remains subject to GitHub image changes, each workflow must explicitly verify `VERSION_CODENAME=resolute` and amd64 before doing project work.

The repository is public pre-alpha development. Public visibility does not imply release readiness and there is no supported ISO/release yet.

## Gate 1 — package build and APT resolution

Workflow: `.github/workflows/package-validation.yml`

Historical baseline status: **GREEN**

It proves for the package state that produced the accepted baseline:

1. development package sources build into DEBs on Ubuntu 26.04;
2. the runner is amd64 Resolute;
3. `supralinux-snap-policy`, `supralinux-base`, `supralinux-settings` and `supralinux-desktop` resolve together through APT;
4. the Snap policy removes installable APT candidates for `snapd` and `plasma-discover-backend-snap` in a fresh APT state;
5. the default package composition does not pull `plasma-session-x11`;
6. Plasma Discover resolves under the policy without pulling the Snap backend.

A candidate SupraLINUX KDE stack must receive its own source-build and APT-closure evidence under `docs/KDE_STACK_QUALIFICATION.md`; this historical green result is not sufficient for adoption.

## Gate 2 — clean rootfs installation

Workflow: `.github/workflows/rootfs-validation.yml`

Historical baseline status: **GREEN**

This gate builds a disposable Ubuntu 26.04 `debootstrap --variant=minbase` rootfs, enables official Ubuntu repositories, then installs the SupraLINUX DEBs for real inside that isolated filesystem.

The Snap policy is installed first. Base/settings/desktop packages are then installed using normal APT behavior. The gate runs `apt-get check` and verifies representative required integration packages including Plasma Wayland, XWayland compatibility, SDDM/KWin Wayland, Polkit, PipeWire, NetworkManager, Bluetooth, KDE portals, Flatpak integration, KRDP, printing, Samba sharing, KWallet, power management and display management.

It also verifies Aurora's SDDM Wayland configuration and rejects Plasma X11 session launchers, Snap components, Ubuntu Desktop, Kubuntu Desktop and GNOME Shell.

This gate proves clean composition, not runtime feature completeness. The candidate KDE stack must repeat equivalent clean-install closure in KSQ-3 before it can replace the historical baseline.

## Gate 3 — C1 kernel + systemd boot

Workflow: `.github/workflows/boot-c1-validation.yml`

Historical KDE 6.6.6 baseline status: **CERTIFIED**

C1 converts the clean Aurora composition into a disposable ext4 VM disk, boots the Ubuntu kernel/initramfs in QEMU and requires the guest to reach a healthy `multi-user.target` state.

The guest must emit exactly one `AURORA_C1_SUCCESS` marker and no `AURORA_C1_FAILURE` marker.

Canonical historical evidence: `docs/validation/AURORA_C1_ACCEPTANCE.md`.

A Frameworks/Plasma/KWin stack replacement triggers a C1 composition/boot smoke regression as part of KDE Stack Qualification.

## Gate 4 — C2 graphical target + SDDM Wayland greeter

Workflow: `.github/workflows/boot-c2-validation.yml`

Historical KDE 6.6.6 baseline status: **CERTIFIED**

C2 boots the same package-defined Aurora system to `graphical.target` with a virtual DRM device and observes a live SDDM greeter running on KWin Wayland. It does not accept merely installed/enabled configuration.

Canonical historical evidence: `docs/validation/AURORA_C2_ACCEPTANCE.md`.

A candidate KWin/Plasma stack must pass C2 again before adoption.

## Gate 5 — C3 Plasma Wayland user session

Workflow: `.github/workflows/boot-c3-validation.yml`

Historical KDE 6.6.6 baseline status: **CERTIFIED**

C3 creates a disposable CI-only user and uses SDDM autologin only inside the generated VM. It validates desktop readiness in bounded stages and requires deterministic guest markers.

Accepted historical scope includes:

- active local disposable-user session;
- `Type=wayland`;
- usable user D-Bus;
- natural `graphical-session.target` readiness;
- KWin Wayland and Plasma shell;
- Plasma user-session targets;
- session environment and Wayland/XWayland sockets;
- first-login Look-and-Feel defaults state;
- Xresources/XWayland state;
- PipeWire/WirePlumber capability;
- Plasma Polkit agent capability;
- XDG portal/KDE backend registration;
- real Qt/XCB smoke test through XWayland;
- stable KWin/Plasma processes through probe completion.

These are readiness/plumbing assertions. They do not substitute for C4 feature workflows such as real privileged actions, real audio streams, Flatpak permission behavior or screen-sharing lifecycle.

Canonical historical evidence: `docs/validation/AURORA_C3_ACCEPTANCE.md`.

A candidate KWin/Plasma stack must pass C3, including XWayland compatibility, again before adoption.

## KDE Stack Qualification — current active gate

Canonical plan: `docs/KDE_STACK_QUALIFICATION.md`.

Override/backport ownership: `docs/KDE_STACK_OVERRIDES.md`.

### KSQ-0 — source and dependency inventory

Status: **CERTIFIED**

Canonical acceptance: `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`.

Canonical engineering commit: `4e7db453f626e78ca72c353ab314e16e00c9003f`.

Inventory workflow: `.github/workflows/ksq-0-source-inventory.yml`

Accepted inventory run: `33231880014`.

Strict dependency workflow: `.github/workflows/ksq-0-dependency-closure.yml`

Accepted strict run: `33231879994`.

The strict gate proves:

- official Plasma 6.7.4 and Frameworks 6.29.0 source manifests validate;
- all 62 direct `supralinux-desktop` roots are classified;
- APT metadata is pinned to Ubuntu snapshot `20260829T022000Z`;
- Resolute is the only binary repository used by the closure model;
- Stonking contributes source metadata only;
- the exact transitive build closure contains 101 source packages;
- all 101 are topologically ordered;
- `UNRESOLVED=0`;
- no source decision remains implicit;
- exactly three external source selections and one packaging build-dependency adaptation are declared and consumed;
- selected external source objects/checksums are audited;
- `kwallet-pam` PAM functional packaging is byte-identical to Debian 6.7.4-3 where required.

The candidate retains Ubuntu ownership for kernel, firmware, Mesa/libdrm, systemd, PipeWire/WirePlumber, NetworkManager, Wayland runtime, Qt and base runtime/compiler libraries.

### KSQ-1 — reproducible source builds

Status: **ACTIVE**

Workflow: `.github/workflows/ksq-1-full-builds.yml`.

The builder consumes the certified 101-source DAG on clean Resolute amd64 runners. Each checkpoint recreates and revalidates the pinned snapshot build environment. Candidate dependencies are transported between jobs only as explicit DEB checkpoint artifacts; Stonking is not enabled as a binary repository.

Build checkpoints are:

- 001–020;
- 021–040;
- 041–060;
- 061–080, followed by the KWallet PAM package-level installation gate;
- 081–101;
- final 101-source manifest/hash validation.

`sbuild` runs unshare-backed against the pinned buildd tarball with build-time network disabled. It receives accumulated candidate DEBs through `--extra-package`, enables normal Debian alternative Build-Depends resolution with `--resolve-alternatives`, and enables the APT uninstallable-dependency explainer.

The alternative-resolver requirement is evidence-based. Full run `33250886255` built nodes 1–39 and failed on node 40 (`kf6-kfilemetadata`) because its valid `libpostproc-dev | hello` relationship was being reduced to the unavailable first alternative by the original sbuild invocation. Diagnostic run `33263391639` proved the resolver cause. Corrective run `33263576164` kept the source, snapshot and prior candidate binaries unchanged, enabled alternative resolution, selected `hello`, and built node 40 successfully. Its artifact `9718028796` has digest `sha256:1808c2e3150c5ee8447a0e0242706bdb89f00e613c617b9a6b983479806caac0`.

Global builder commit `fe12df912217d44465a7a613d79ba3f523d4e700` incorporates that proven fix. It also records `.build`, `.buildinfo`, `.changes`, partial DEBs/DDEBs, hashes, first failed source/order and successful DEBs already produced in a checkpoint before returning failure, so a package failure remains diagnosable without guessing from a workflow status.

Current full regression run for the global builder: `33264059201`. It is **ACTIVE**, not accepted yet.

Canonical bootstrap evidence remains run `33248631454`, artifact `9713725769`, digest `sha256:ee26c3f3421adcf4e64d351e10ba61c2bc890ba8c4bfded4b7e37dcb72fd9c7d`.

Even a future 101/101 green full build does not by itself close KSQ-1. Reproducibility must be demonstrated by repeated byte-for-byte build comparison under controlled variations using the Debian/Ubuntu reproducible-build tooling available on Resolute, with diagnostic evidence retained for any divergence.

Any change to the certified release set, source selections, packaging overrides, snapshot or relevant platform boundary reopens the corresponding KSQ-0 regression first.

The later qualification sequence remains:

- KSQ-2 temporary/testing SupraLINUX APT repository and binary dependency closure;
- KSQ-3 clean installation;
- KSQ-4 upgrade from the historical 6.6.6/KF 6.24 baseline;
- KSQ-5 rollback/recovery;
- KSQ-6 C1-C3 regressions;
- KSQ-7 fresh C4.0 runtime-surface reconciliation;
- KSQ-8 compatibility-workaround review;
- KSQ-9 security/update ownership;
- KSQ-10 explicit GO/NO-GO.

Until KSQ-10 closes, C4.1 and later feature work remains paused.

## C4 feature integration certification

Status: **PAUSED; historical C4.0 CERTIFIED on KDE 6.6.6; historical C4.1a incremental evidence preserved**

C4 is split into manageable subgates defined by `docs/C4_CERTIFICATION.md` and backed by the version-scoped capability inventory in `docs/PLASMA_INTEGRATION_MATRIX.md`.

### Historical C4.0 — Surface and contract inventory

Workflow: `.github/workflows/c4-0-surface-validation.yml`

Historical baseline status: **CERTIFIED**

C4.0 boots the package-defined Aurora desktop, inventories the runtime-exposed Plasma/KWin/KDED/KIO/portal surface, records package ownership and versions, compares the result with version-controlled manifests, and rejects unknown/missing surfaces or unowned capability IDs.

The latest accepted historical C4.0 revalidation recorded:

- 100 Plasma KCM IDs;
- 62 direct `supralinux-desktop` dependencies;
- 3 installed portal descriptors;
- 29 KWin surfaces;
- 123 Plasma/KDED/KIO integration surfaces;
- 36 direct `plasma-desktop` feature `Recommends`.

All unknown, missing and unresolved-owner result sets were empty in the accepted run recorded by `docs/C4_CERTIFICATION.md`.

Canonical historical evidence: `docs/validation/AURORA_C4_0_ACCEPTANCE.md`.

C4.0 is a coverage gate, not a feature-functionality gate. Its historical PASS must not be propagated to the candidate KDE stack or to C4.1-C4.15 capabilities.

### Historical C4.1 work

The repository contains accepted historical C4.1a evidence for Activities and Virtual Desktops plus C4.1b File Search/Baloo investigation/harness work. C4.1 never closed.

Do not continue feature-by-feature C4 implementation until KDE Stack Qualification produces a GO/NO-GO. If the new stack is adopted, regenerate C4.0 first and then re-run version-sensitive historical PASS capabilities before treating them as release-candidate PASS results.

Later subgates remain:

- C4.2 Polkit/KWallet/privileged actions;
- C4.3 NetworkManager/Plasma-NM/VPN;
- C4.4 PipeWire/WirePlumber/audio;
- C4.5 Bluetooth/BlueDevil;
- C4.6 Flatpak/portal routing;
- C4.7 capture/screen sharing;
- C4.8 KRDP/RDP;
- C4.9 printing/CUPS;
- C4.10 UDisks/Solid/removable media;
- C4.11 Samba/KIO/KIO-FUSE;
- C4.12 power/platform integration;
- C4.13 locale/translations/XDG dirs;
- C4.14 accessibility;
- C4.15 auxiliary/direct-dependency closure.

A KCM/process/service merely existing never produces a feature-level C4 PASS. Each capability must execute and observe a real backend action according to the C4 contract.

## Regression policy

Certification evidence is version-scoped. Regression is required when a later product change can plausibly affect accepted scope.

Examples:

- documentation-only qualification/C4 changes: no boot/session or KSQ rerun;
- harness/fixture-only additions that do not alter the product image: no automatic C1-C3 rerun;
- change to a KSQ-0 release set/source selection/override/pinned snapshot: rerun affected KSQ-0 inventory/closure before downstream evidence is reusable;
- build-harness changes that can alter Build-Depends resolution or output invalidate affected KSQ-1 build evidence even when package sources are unchanged;
- Frameworks/Plasma/KWin stack replacement: C1 composition/boot smoke + C2 + C3 + fresh C4.0 before feature certification resumes;
- later Plasma/KWin/session/XWayland package or configuration changes within an accepted stack: C3 regression, plus C2 if greeter infrastructure overlaps, and C4.0 if the effective surface can change;
- SDDM/KWin greeter changes: C2 and normally C3;
- kernel/base/systemd/initramfs changes: C1 plus affected later gates;
- `supralinux-desktop` dependency or relevant Plasma/KWin/KIO/KDED/portal package-graph changes: C4.0 regression.

The triggering change must record the regression reason. Historical evidence remains attached to the stack that produced it.

## Evidence model

Serial guest markers remain the primary deterministic evidence channel for VM gates. A green workflow or QEMU exit code alone is insufficient.

For KDE Stack Qualification and C4, evidence additionally includes source/package manifests, build logs, APT transactions, product/fixture package manifests, ownership/version inventories, source checksums, explicit override records and targeted backend/service logs. Product dependencies and CI-only fixture dependencies must be reported separately.

KSQ-1 failed checkpoints must retain the first failed source/order and the actual sbuild diagnostics. A workflow-level failure string alone is not sufficient root-cause evidence.

## Storage policy

Large VM/rootfs images remain ephemeral and out of Git. Validation preserves compact serial logs and targeted diagnostics. Persistent release packages belong in the future SupraLINUX APT repository rather than Actions artifact storage.
