# Aurora Base System — Ubuntu 26.04 LTS

Status: **declarative candidate validated through clean-rootfs and C1-C3; release freeze still pending C4/Phase 1 completion**.

SupraLINUX does not start from Ubuntu Desktop and then remove GNOME. Aurora starts from Ubuntu's base system and adds the SupraLINUX desktop layer deliberately.

## Candidate composition

The current `supralinux-base` candidate is:

```text
ubuntu-minimal
ubuntu-standard
linux-generic
linux-firmware
firmware-sof-signed
wireless-regdb
```

This is intentionally a base/platform definition, not a desktop definition. NetworkManager, PipeWire, Plasma, SDDM and other graphical/session components belong to `supralinux-desktop` unless a later architectural reason moves them.

## Why `ubuntu-minimal`

Ubuntu 26.04 describes `ubuntu-minimal` as the minimal core of Ubuntu. It establishes the Ubuntu-supported base including APT, init/system plumbing, udev, locales, users/login tools, netplan, time-zone data, Ubuntu archive keys and other core utilities.

Using it keeps Aurora aligned with the Ubuntu LTS base rather than reconstructing an arbitrary Debian-like userspace package by package.

## Why `ubuntu-standard`

`ubuntu-standard` adds normal non-GUI system utilities expected on a general-purpose Ubuntu installation: DNS tools, rescue BusyBox, cron, filesystem/disk tools, hardware inspection tools, log rotation, man pages, nftables tooling, rsync, strace, USB/PCI utilities, wget, xz tools and related basics.

It does **not** imply Ubuntu Desktop or GNOME and it does not currently depend on or recommend `snapd`.

For SupraLINUX this is preferable to artificial minimalism: a desktop OS should not omit ordinary system/admin utilities merely to make an ISO number smaller.

## Why `linux-generic`

Aurora follows Ubuntu's generic kernel track. `linux-generic` is the supported metapackage for the complete generic kernel and headers.

Keeping headers in the standard base is intentional for the first generation because:

- third-party/DKMS modules may need them;
- proprietary-driver workflows may need them;
- they keep the installed kernel/header pair aligned through normal Ubuntu updates.

SupraLINUX must not pin a specific `N.N.N-N` kernel package. The metapackage owns the moving supported kernel version.

## Firmware policy

Ubuntu 26.04 split `linux-firmware` into a metapackage over vendor-specific firmware packages. SupraLINUX uses the full `linux-firmware` metapackage rather than `linux-firmware-minimal` because Aurora targets a general-purpose desktop across diverse hardware.

`firmware-sof-signed` is explicit even though `linux-firmware` recommends it, because Intel SOF audio firmware is part of the hardware baseline we intend to support rather than an optional image-size optimization.

`wireless-regdb` is explicit because correct wireless regulatory data is part of a complete Wi-Fi platform.

## What is deliberately NOT in `supralinux-base`

- Ubuntu Desktop / GNOME
- `kubuntu-desktop`
- Plasma/KDE
- `snapd`
- server stacks merely because Ubuntu Server includes them
- Docker/container tooling
- developer toolchains
- arbitrary applications
- SupraLINUX branding/settings

Those belong in other layers or are not default product requirements.

## Layer boundary

```text
Ubuntu archive
     │
     ▼
supralinux-base
  ├─ Ubuntu minimal core
  ├─ Ubuntu standard utilities
  ├─ Ubuntu generic kernel + headers
  └─ broad firmware baseline
     │
     ▼
supralinux-desktop
  ├─ Plasma / Wayland / KWin
  ├─ desktop backends
  └─ integration features
     │
     ▼
settings / apps / artwork / installer
```

## Validation state

The candidate has already demonstrated:

1. dependencies resolve from official Ubuntu 26.04 repositories;
2. `snapd` is absent while `supralinux-snap-policy` is active;
3. the package-defined system installs coherently in an isolated clean rootfs;
4. the Ubuntu generic kernel/initramfs boots the composed Aurora filesystem in C1;
5. the system reaches SDDM/KWin Wayland graphical boot in C2;
6. a real Plasma Wayland user session reaches stable runtime in C3;
7. adding `supralinux-desktop` does not require Ubuntu Desktop or Kubuntu Desktop metapackages.

These results validate the current development candidate; they do not release-freeze `supralinux-base` or prove broad physical-hardware compatibility.

## Remaining freeze conditions

Before the base is release-frozen:

- C4 must complete the desktop feature/integration audit and expose any base/desktop layer-boundary defect;
- later hardware validation must cover representative kernel/firmware paths;
- normal Ubuntu security/update behavior must continue without SupraLINUX pinning kernel internals;
- the final release/ISO composition must retain the documented layer boundary.

This candidate may still be reduced or expanded from evidence, but never for cosmetic package-count goals.
