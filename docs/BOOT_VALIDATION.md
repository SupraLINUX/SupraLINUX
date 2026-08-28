# Aurora Boot and Feature Validation

This document defines the validation layers after the clean-rootfs gate.

The clean-rootfs gate proves that SupraLINUX packages can be installed coherently on a clean Ubuntu 26.04 base. It does **not** by itself prove boot, graphical login, user-session health or feature integration. Validation therefore advances in explicit stages. A later stage must not be treated as passed because an earlier one succeeded.

Current canonical gate state:

```text
clean-rootfs — GREEN
C1 — GREEN / CERTIFIED
C2 — GREEN / CERTIFIED
C3 — GREEN / CERTIFIED
C4.0 — GREEN / CERTIFIED
C4.1 — CURRENT IMPLEMENTATION TARGET
C5 — LOCKED UNTIL C4
```

Acceptance records under `docs/validation/` are authoritative. Do not reopen C1-C3 or C4.0 without a real regression trigger.

## Stage C1 — Kernel + systemd boot

Status: **CERTIFIED**

Goal: boot the installed Aurora filesystem in a disposable VM and prove that a real Linux boot reaches userspace correctly.

Required evidence includes:

- kernel boots successfully;
- root filesystem mounts read/write;
- systemd becomes PID 1;
- machine reaches at least `multi-user.target`;
- no emergency/rescue target;
- `apt-get check` succeeds after boot;
- SupraLINUX packages remain installed;
- Snap remains blocked/absent;
- required system services are installed and loadable;
- SDDM is enabled for graphical boot.

C1 is intentionally not a Plasma test.

Canonical evidence: `docs/validation/AURORA_C1_ACCEPTANCE.md`.

## Stage C2 — Graphical target + SDDM Wayland greeter

Status: **CERTIFIED**

Goal: prove that the disposable VM reaches graphical boot and Aurora's configured SDDM greeter actually runs on KWin Wayland.

Required evidence includes:

- `graphical.target` reached;
- SDDM starts without fatal configuration error;
- `supralinux-settings` provides Aurora's SDDM Wayland configuration;
- `DisplayServer=wayland` and KWin Wayland compositor command are active;
- graphical seat/logind integration exists;
- appropriate virtual graphics device exists;
- `kwin_wayland` and `sddm-greeter` run for the SDDM user;
- XWayland remains installed for application compatibility;
- Plasma X11 desktop session is absent from the default Aurora composition.

C2 does not certify a normal Plasma user session.

Canonical evidence: `docs/validation/AURORA_C2_ACCEPTANCE.md`.

## Stage C3 — Plasma Wayland user session

Status: **CERTIFIED**

Goal: launch an actual disposable user session and prove the SupraLINUX baseline runs as Plasma on Wayland while retaining intended XWayland application compatibility.

The test user and CI autologin remain test-only and are not product defaults.

C3 acceptance includes:

- active local disposable-user login;
- `Type=wayland`;
- usable user D-Bus;
- `graphical-session.target` becoming active through normal Plasma startup rather than being manufactured by the probe;
- KWin Wayland and Plasma shell;
- Plasma Wayland/workspace targets;
- real session environment and Wayland/XWayland display sockets;
- first-login Look-and-Feel defaults persistence;
- Xresources/XWayland state;
- PipeWire/WirePlumber capability;
- Plasma Polkit agent capability;
- XDG portal broker/KDE backend registration;
- a real Qt/XCB compatibility smoke test through XWayland using installed `systemsettings`;
- stable KWin/Plasma PIDs through the end of the probe.

These C3 checks prove session readiness and selected plumbing only. They do not certify the full product workflows for Polkit, KWallet, audio, portals or other C4 features.

Canonical evidence: `docs/validation/AURORA_C3_ACCEPTANCE.md`.

## Stage C4 — Feature integration certification

Status: **ACTIVE; C4.0 CERTIFIED; C4.1 CURRENT**

C4 starts only after the real Wayland user session is reproducibly available. Its purpose is to certify the feature matrix end-to-end.

Canonical documents:

- capability inventory: `docs/PLASMA_INTEGRATION_MATRIX.md`;
- execution/acceptance contract: `docs/C4_CERTIFICATION.md`;
- package/KCM research inputs: `docs/KCM_AUDIT.md` and `docs/PLASMA_PACKAGE_AUDIT.md`;
- portal policy: `docs/PORTAL_POLICY.md`;
- reproduced/external blockers: `docs/UPSTREAM_BLOCKERS.md`.

A KCM merely opening never counts as feature completeness.

### C4.0 — Surface and contract inventory

Status: **CERTIFIED**

The accepted runtime inventory reconciles the package-defined Aurora surface against version-controlled contracts and records package ownership/version evidence.

Accepted counts:

- 100 Plasma KCM IDs;
- 61 direct `supralinux-desktop` dependencies;
- 3 installed portal descriptors;
- 29 KWin surfaces;
- 119 Plasma/KDED/KIO integration surfaces;
- 36 direct `plasma-desktop` feature `Recommends`.

All unknown/missing sets and all unresolved-owner sets were empty.

Canonical evidence: `docs/validation/AURORA_C4_0_ACCEPTANCE.md`.

C4.0 is now closed. Re-run it when a later package/dependency/SRU change can alter the effective shipped/discovered surface. A documentation-only status update does not invalidate C4.0.

### C4.1 — System Settings / KWin / software-only desktop behavior

Status: **CURRENT IMPLEMENTATION TARGET**

Activities, Baloo/search, keyboard/shortcuts, workspace/session behavior, KWin effects/scripts/virtual desktops/decorations/rules/XWayland policy/window behavior/screen edges/task switcher and other software-only mapped KCMs.

Each capability requires an observable state/action result, persistence/cleanup where relevant and session stability. Mere plugin/KCM discovery is already covered by C4.0 and is not sufficient here.

### C4.2 — Polkit + KWallet + privileged actions

Exercise real privileged operations and a password-based KWallet/PAM login flow. Service/process presence alone is insufficient.

### C4.3 — NetworkManager + Plasma-NM + VPN

Exercise a dedicated virtual NIC plus controlled OpenVPN/OpenConnect endpoints. Wi-Fi/real modem claims remain hardware-scoped unless a faithful fixture is explicitly documented.

### C4.4 — PipeWire + WirePlumber + Plasma audio

Exercise real streams against virtual audio endpoints and prove volume/mute/routing state changes through the actual backend.

### C4.5 — Bluetooth + BlueDevil

A CI-only virtual HCI fixture may prove BlueZ/BlueDevil software integration. Physical peripheral pairing and Bluetooth audio remain hardware follow-up.

### C4.6 — Flatpak + portal routing

Use a local test Flatpak. Record effective portal routing and prove real sandbox/permission behavior. Resolve the KDE-primary/GTK-fallback policy with runtime evidence.

### C4.7 — Screenshot / screencast / screen sharing

Exercise the real Wayland KWin → portal → PipeWire path. Repeated screen-sharing lifecycle tests are required because of the tracked upstream regression candidate.

### C4.8 — KRDP / RDP

Use an external RDP client role and exercise actual server/session lifecycle. KRDC is only certified if it becomes a shipped baseline application rather than remaining merely recommended.

### C4.9 — Printing / CUPS

Use a controlled virtual IPP target. Submit a real job, inspect queue lifecycle, cancellation and a failure path.

### C4.10 — UDisks / Solid / removable media

Use hot-pluggable virtual removable storage and exercise mount/read-write/unmount/eject plus automount policy.

### C4.11 — Samba / KIO / KIO-FUSE

Test both remote SMB consumption and local KDE/Samba sharing from an external client.

### C4.12 — Power management

Exercise PowerDevil according to capabilities exposed by the VM, including suspend/resume where credible. Hardware battery/brightness/lid/profile claims remain separate.

### C4.13 — Locale / translations / XDG user directories

Test clean pre-first-login locale establishment for at least `en_US.UTF-8` and `es_AR.UTF-8`. Installer-selected locale is not claimed until Phase 4 because Calamares is not yet implemented.

### C4.14 — Accessibility

Exercise AT-SPI, Orca/Speech Dispatcher and representative exposed KWin accessibility behavior.

### C4.15 — Auxiliary integration / direct-dependency closure

Every direct `supralinux-desktop` dependency must finish C4 as tested/justified, hardware-dependent/justified, or demoted/removed. No dependency remains merely because it was part of an early broad candidate.

## Stage C5 — Interactive/manual VM QA

Status: **LOCKED UNTIL C4 IS COMPLETE**

Some behavior is unsuitable for fully headless certification. After C4 is stable, an interactive VM becomes the first human-visible Aurora desktop QA stage.

Examples:

- SDDM visual behavior;
- Plasma first-login experience;
- display configuration UX;
- clipboard and drag/drop behavior;
- network dialogs;
- printer dialogs;
- Bluetooth pairing UI;
- portal chooser behavior;
- screen-sharing prompts;
- localization consistency;
- XWayland application behavior;
- general desktop regressions.

C5 precedes ISO work and must still use the package-defined system rather than manual remastering.

## CI constraints

- Prefer hardware virtualization when available, but never infer physical hardware support from QEMU.
- Keep VM images disposable and out of Git.
- Keep CI-only users, passwords, autologin, fixture packages and diagnostics outside product packages.
- Separate product dependencies from CI fixture dependencies in logs/manifests.
- Preserve serial logs and targeted diagnostics on failure.
- A guest success marker is required; a green workflow or QEMU exit code alone is insufficient.
- Keep supervisor timeouts finite but longer than the sum of bounded readiness waits and expected QEMU overhead.
- Avoid shell constructs that create harness-only false negatives under `pipefail`.
- Do not hide warnings merely to make CI green; classify them.
- Do not remove X11 compatibility components merely for protocol purity.
- Do not change multiple product variables at once when a failure can first be isolated.

## Regression policy

C1-C3 are not rerun automatically for every C4 documentation/harness change. C4.0 is likewise not rerun solely because its acceptance/status documentation changes.

Re-run only the certified scopes plausibly affected by a product change. Examples:

- kernel/base/systemd/initramfs changes → C1 plus affected later gates;
- SDDM/KWin greeter changes → C2 and normally C3;
- Plasma/KWin/session/XWayland composition changes → C3, and C2 when shared greeter infrastructure is affected;
- relevant Plasma/KWin/KIO/KDED/portal package-graph or `supralinux-desktop` dependency changes → C4.0;
- documentation-only C4 changes → no C1-C3 regression and no C4.0 invalidation.

The change that triggers regression must record why the older gate is in scope.

## Phase 1 milestone

The executable path is now:

```text
Ubuntu 26.04 clean base
        ↓
SupraLINUX packages + settings
        ↓
clean-rootfs ✅
        ↓
C1 kernel/systemd ✅
        ↓
C2 SDDM + KWin Wayland greeter ✅
        ↓
C3 real Plasma Wayland user session + XWayland ✅
        ↓
C4.0 complete surface/contract inventory ✅
        ↓
C4.1 feature behavior certification ← current work
        ↓
C4.2-C4.15 remaining feature subgates
        ↓
re-evaluate/freeze candidate desktop dependencies
        ↓
C5 manual VM QA
```

Only after C4 evidence closes the selected feature surface should the exact `supralinux-desktop` dependency set be considered ready to freeze.
