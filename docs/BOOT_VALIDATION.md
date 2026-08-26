# Aurora Boot Validation

This document defines the next validation layer after the clean-rootfs gate.

The clean-rootfs gate proves that SupraLINUX packages can be installed coherently on a clean Ubuntu 26.04 base. It does **not** prove that the resulting system boots, that systemd reaches a healthy state, that SDDM works, or that Plasma actually starts as a Wayland session.

Boot validation therefore advances in explicit stages. A later stage must not be treated as passed because an earlier one succeeded.

## Stage C1 — Kernel + systemd boot

Goal: boot the installed Aurora filesystem in a disposable VM and prove that a real Linux boot reaches userspace correctly.

Initial CI approach:

1. Reuse the same package build and clean Ubuntu 26.04 composition used by the rootfs gate.
2. Convert the resulting rootfs into a disposable ext4 disk image.
3. Boot the Ubuntu kernel and initramfs from that rootfs in QEMU.
4. Capture the serial console as a CI artifact.
5. Require systemd to reach a defined target without entering emergency mode.

Required evidence:

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

This stage is intentionally not a Plasma test.

## Stage C2 — Graphical target + SDDM

Goal: prove that the same disposable VM can reach the graphical boot path.

Required evidence:

- `graphical.target` is reached;
- SDDM starts without a fatal configuration error;
- an appropriate virtual graphics device is detected;
- required seat/logind integration exists;
- the system does not fall back to a text-only boot because of missing desktop dependencies.

CI may use software rendering and virtual hardware. Passing here does not imply real-hardware graphics support.

## Stage C3 — Plasma Wayland session

Goal: launch an actual disposable user session and prove that the SupraLINUX baseline runs as Plasma on Wayland.

The test user and any automatic login configuration used by CI are test-only and must never become product defaults.

Required evidence from inside the session:

- `XDG_SESSION_TYPE=wayland`;
- KWin Wayland is running;
- Plasma shell is running;
- a user D-Bus session is available;
- KDE portal backend is available;
- PipeWire user services can start;
- KWallet/PAM integration does not prevent login;
- Polkit KDE agent can start;
- no immediate Plasma/KWin crash loop.

The guest should emit a machine-readable success/failure marker to the serial console or another deterministic CI channel. Merely seeing `sddm.service` active is not enough.

## Stage C4 — Feature integration smoke tests

Only after a real Wayland session is reproducibly available do we start testing the feature matrix.

Initial groups:

- System Settings/KCM availability;
- NetworkManager + Plasma NM;
- PipeWire/audio plumbing;
- Bluetooth backend;
- Flatpak permissions KCM;
- KDE portals;
- screen capture/screen sharing plumbing;
- KRDP/KRDC integration where applicable;
- printing/CUPS;
- Samba/KIO network sharing;
- removable media;
- power management;
- locale/language/XDG user directories.

A KCM merely opening does not count as feature completeness. Tests must verify the backend or service path that makes the control functional.

## Stage C5 — Interactive/manual VM QA

Some behavior is unsuitable for a fully headless CI assertion. Once C1-C4 are stable, an interactive VM becomes the first human-visible Aurora desktop test.

Examples:

- SDDM visual behavior;
- Plasma first-login experience;
- display configuration UX;
- clipboard and drag/drop behavior;
- network dialogs;
- printer dialogs;
- Bluetooth pairing UI;
- portal chooser behavior;
- screen sharing prompts;
- localization consistency;
- general desktop regressions.

This stage precedes ISO work. The VM should still be produced from the package-defined system rather than from manual distro-remastering steps.

## CI constraints

- Prefer hardware virtualization when the runner exposes it, but do not require it for correctness; a software-emulated fallback may be used for C1 if practical.
- Do not claim GPU/hardware compatibility from a QEMU virtual-GPU test.
- Keep VM images disposable and out of Git.
- Keep CI-only users, passwords, autologin and diagnostic services outside product packages.
- Preserve serial logs and targeted diagnostics on failure.
- Do not hide warnings merely to make CI green; classify them as expected VM/chroot limitations or actionable defects.

## Phase 1 boot milestone

The first executable target after the clean-rootfs gate is therefore:

```text
Ubuntu 26.04 clean base
        ↓
SupraLINUX packages
        ↓
bootable disposable VM
        ↓
systemd
        ↓
graphical.target / SDDM
        ↓
Plasma Wayland test session
```

Only after this works repeatedly should the candidate `supralinux-desktop` dependency set be considered ready to freeze for the Phase 1 baseline.
