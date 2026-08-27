# Aurora Boot Validation

This document defines the validation layers after the clean-rootfs gate.

The clean-rootfs gate proves that SupraLINUX packages can be installed coherently on a clean Ubuntu 26.04 base. It does **not** by itself prove that the resulting system boots, that systemd reaches a healthy state, that SDDM works, or that Plasma actually starts as a Wayland session.

Boot validation therefore advances in explicit stages. A later stage must not be treated as passed because an earlier one succeeded.

## Stage C1 — Kernel + systemd boot

Goal: boot the installed Aurora filesystem in a disposable VM and prove that a real Linux boot reaches userspace correctly.

CI approach:

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

## Stage C2 — Graphical target + SDDM Wayland greeter

Goal: prove that the same disposable VM can reach the graphical boot path and that Aurora's configured SDDM greeter actually runs on KWin Wayland.

Required evidence:

- `graphical.target` is reached;
- SDDM starts without a fatal configuration error;
- `supralinux-settings` installs Aurora's SDDM Wayland configuration;
- the SDDM configuration selects `DisplayServer=wayland` and `kwin_wayland` as the greeter compositor;
- an appropriate virtual graphics device is detected;
- required seat/logind integration exists;
- a `kwin_wayland` process and `sddm-greeter` process are running for the SDDM user;
- `xwayland` remains installed as part of the Plasma Wayland compatibility path;
- the Plasma X11 desktop session is not part of the default Aurora composition;
- the system does not fall back to a text-only boot because of missing desktop dependencies.

The SDDM Wayland path is not accepted merely because a configuration file exists. C2 must observe a live KWin Wayland greeter in the VM. If that path has a blocking regression, the validation must fail rather than silently falling back to an untested display-server mode.

CI may use software rendering and virtual hardware. Passing here does not imply real-hardware graphics support.

## Stage C3 — Plasma Wayland session

Goal: launch an actual disposable user session and prove that the SupraLINUX baseline runs as Plasma on Wayland while retaining application compatibility expected from a complete Plasma desktop.

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
- no immediate Plasma/KWin crash loop;
- XWayland is available and a small disposable X11 client can start inside the Wayland session.

The XWayland check is a compatibility test, not an alternative desktop-session mode. Aurora does not remove X11 compatibility libraries or components merely to satisfy a superficial "Wayland-only" label.

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
- XWayland application behavior;
- general desktop regressions.

This stage precedes ISO work. The VM should still be produced from the package-defined system rather than from manual distro-remastering steps.

## CI constraints

- Prefer hardware virtualization when the runner exposes it, but do not require it for correctness; a software-emulated fallback may be used for C1 if practical.
- Do not claim GPU/hardware compatibility from a QEMU virtual-GPU test.
- Keep VM images disposable and out of Git.
- Keep CI-only users, passwords, autologin and diagnostic services outside product packages.
- Preserve serial logs and targeted diagnostics on failure.
- Do not hide warnings merely to make CI green; classify them as expected VM/chroot limitations or actionable defects.
- Do not remove X11 compatibility components merely to make the package set look more Wayland-pure; feature completeness has priority.

## Phase 1 boot milestone

The executable path is:

```text
Ubuntu 26.04 clean base
        ↓
SupraLINUX packages + settings
        ↓
bootable disposable VM
        ↓
systemd
        ↓
graphical.target / SDDM on KWin Wayland
        ↓
Plasma Wayland test session + XWayland compatibility
```

Only after this works repeatedly should the candidate `supralinux-desktop` dependency set be considered ready to freeze for the Phase 1 baseline.
