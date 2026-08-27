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

## Next executable stage — C4 feature integration certification

Status: **CONTRACT DEFINED; HARNESS IMPLEMENTATION PENDING**

C4 is split into manageable subgates defined by `docs/C4_CERTIFICATION.md` and backed by the canonical capability inventory in `docs/PLASMA_INTEGRATION_MATRIX.md`.

The first implementation target is:

**C4.0 — Surface and contract inventory**

C4.0 must inventory the runtime-exposed Plasma/KWin/integration surface and prove that every in-scope visible surface and every direct `supralinux-desktop` dependency has a matrix/policy owner. Unknown exposed surfaces are failures.

No package dependency changes should be made for C4 feature defects before C4.0 establishes complete coverage.

Later subgates cover:

- C4.1 System Settings/KWin software behavior;
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

A KCM/process/service merely existing never produces a C4 PASS. Each capability must execute and observe a real backend action according to the C4 contract.

## Regression policy

C1-C3 stay closed unless a later product change can plausibly affect their accepted scope.

Examples:

- documentation-only C4 changes: no regression run;
- C4 harness/fixture-only additions that do not alter the product image: no automatic C1-C3 rerun;
- Plasma/KWin/session/XWayland package or configuration changes: C3 regression, plus C2 if greeter infrastructure overlaps;
- SDDM/KWin greeter changes: C2 and normally C3;
- kernel/base/systemd/initramfs changes: C1 plus affected later gates.

The triggering change should record the regression reason.

## Evidence model

Serial guest markers remain the primary deterministic evidence channel for VM gates. A green workflow or QEMU exit code alone is insufficient.

For C4, evidence additionally includes a machine-readable capability result manifest, product/fixture package manifests and targeted backend/service logs. Product dependencies and CI-only fixture dependencies must be reported separately.

## Storage policy

Large VM/rootfs images remain ephemeral and out of Git. Validation preserves compact serial logs and targeted diagnostics. Persistent release packages belong in the future SupraLINUX APT repository rather than Actions artifact storage.
