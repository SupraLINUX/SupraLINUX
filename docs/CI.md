# SupraLINUX CI — Aurora validation

SupraLINUX CI validates packaging, clean-system composition and real VM behavior against Ubuntu 26.04 LTS (`resolute`), the base generation used by Aurora.

## Runner

Workflows use GitHub's `ubuntu-26.04` x64 runner. While that runner image remains subject to GitHub image changes, each workflow must explicitly verify `VERSION_CODENAME=resolute` and amd64 before doing project work.

The repository is public pre-alpha development. Public visibility does not imply release readiness and there is no supported ISO/release yet.

## Gate 1 — package build and APT resolution

Workflow: `.github/workflows/package-validation.yml`

Status: **GREEN**

It proves:

1. development package sources build into DEBs on Ubuntu 26.04;
2. the runner is amd64 Resolute;
3. `supralinux-snap-policy`, `supralinux-base`, `supralinux-settings` and `supralinux-desktop` resolve together through APT;
4. the Snap policy removes installable APT candidates for `snapd` and `plasma-discover-backend-snap` in a fresh APT state;
5. the default package composition does not pull `plasma-session-x11`;
6. Plasma Discover resolves under the policy without pulling the Snap backend.

## Gate 2 — clean rootfs installation

Workflow: `.github/workflows/rootfs-validation.yml`

Status: **GREEN**

This gate builds a disposable Ubuntu 26.04 `debootstrap --variant=minbase` rootfs, enables official Ubuntu repositories, then installs the SupraLINUX DEBs for real inside that isolated filesystem.

The Snap policy is installed first. Base/settings/desktop packages are then installed using normal APT behavior. The gate runs `apt-get check` and verifies representative required integration packages including Plasma Wayland, XWayland compatibility, SDDM/KWin Wayland, Polkit, PipeWire, NetworkManager, Bluetooth, KDE portals, Flatpak integration, KRDP, printing, Samba sharing, KWallet, power management and display management.

It also verifies Aurora's SDDM Wayland configuration and rejects Plasma X11 session launchers, Snap components, Ubuntu Desktop, Kubuntu Desktop and GNOME Shell.

This gate proves clean composition, not runtime feature completeness.

## Gate 3 — C1 kernel + systemd boot

Workflow: `.github/workflows/boot-c1-validation.yml`

Status: **CERTIFIED**

C1 converts the clean Aurora composition into a disposable ext4 VM disk, boots the Ubuntu kernel/initramfs in QEMU and requires the guest to reach a healthy `multi-user.target` state.

The guest must emit exactly one `AURORA_C1_SUCCESS` marker and no `AURORA_C1_FAILURE` marker.

Canonical evidence: `docs/validation/AURORA_C1_ACCEPTANCE.md`.

## Gate 4 — C2 graphical target + SDDM Wayland greeter

Workflow: `.github/workflows/boot-c2-validation.yml`

Status: **CERTIFIED**

C2 boots the same package-defined Aurora system to `graphical.target` with a virtual DRM device and observes a live SDDM greeter running on KWin Wayland. It does not accept merely installed/enabled configuration.

Canonical evidence: `docs/validation/AURORA_C2_ACCEPTANCE.md`.

## Gate 5 — C3 Plasma Wayland user session

Workflow: `.github/workflows/boot-c3-validation.yml`

Status: **CERTIFIED**

C3 creates a disposable CI-only user and uses SDDM autologin only inside the generated VM. It validates desktop readiness in bounded stages and requires deterministic guest markers.

Accepted scope includes:

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

Canonical evidence: `docs/validation/AURORA_C3_ACCEPTANCE.md`.

## C4 feature integration certification

Status: **C4.0 CERTIFIED; C4.1 NEXT**

C4 is split into manageable subgates defined by `docs/C4_CERTIFICATION.md` and backed by the canonical capability inventory in `docs/PLASMA_INTEGRATION_MATRIX.md`.

### C4.0 — Surface and contract inventory

Workflow: `.github/workflows/c4-0-surface-validation.yml`

Status: **CERTIFIED**

C4.0 boots the package-defined Aurora desktop, inventories the runtime-exposed Plasma/KWin/KDED/KIO/portal surface, records package ownership and versions, compares the result with version-controlled manifests, and rejects unknown/missing surfaces or unowned capability IDs.

Accepted C4.0 coverage includes exact reconciliation of:

- 100 Plasma KCM IDs;
- 61 direct `supralinux-desktop` dependencies;
- 3 installed portal descriptors;
- 29 KWin surfaces;
- 119 Plasma/KDED/KIO integration surfaces;
- 36 direct `plasma-desktop` feature `Recommends`.

All unknown, missing and unresolved-owner result sets were empty in the accepted run.

Canonical evidence: `docs/validation/AURORA_C4_0_ACCEPTANCE.md`.

C4.0 is a coverage gate, not a feature-functionality gate. Its PASS must not be propagated to C4.1-C4.15 capabilities.

### Current implementation target — C4.1

C4.1 owns System Settings, KWin and software-only/virtualizable Plasma shell behavior defined by the canonical matrix. It must perform real state/action assertions rather than treating a KCM or plugin load as success.

Later subgates cover:

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

C1-C3 stay closed unless a later product change can plausibly affect their accepted scope. C4.0 likewise stays closed unless a later change can alter the effective shipped/discovered Plasma surface or dependency graph.

Examples:

- documentation-only C4 changes: no C1-C3 regression run and no C4.0 invalidation;
- C4 harness/fixture-only additions that do not alter the product image: no automatic C1-C3 rerun;
- Plasma/KWin/session/XWayland package or configuration changes: C3 regression, plus C2 if greeter infrastructure overlaps, and C4.0 if the effective surface can change;
- SDDM/KWin greeter changes: C2 and normally C3;
- kernel/base/systemd/initramfs changes: C1 plus affected later gates;
- `supralinux-desktop` dependency or relevant Plasma/KWin/KIO/KDED/portal package-graph changes: C4.0 regression.

The triggering change should record the regression reason.

## Evidence model

Serial guest markers remain the primary deterministic evidence channel for VM gates. A green workflow or QEMU exit code alone is insufficient.

For C4, evidence additionally includes capability manifests, product/fixture package manifests, ownership/version inventories and targeted backend/service logs. Product dependencies and CI-only fixture dependencies must be reported separately.

## Storage policy

Large VM/rootfs images remain ephemeral and out of Git. Validation preserves compact serial logs and targeted diagnostics. Persistent release packages belong in the future SupraLINUX APT repository rather than Actions artifact storage.
