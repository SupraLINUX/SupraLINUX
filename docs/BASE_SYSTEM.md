# Aurora Base System — Ubuntu 26.04 LTS

Status: **first declarative candidate; clean build/install validation pending**.

SupraLINUX does not start from Ubuntu Desktop and then remove GNOME. Aurora starts from Ubuntu's base system and adds the SupraLINUX desktop layer deliberately.

## Candidate composition

The first `supralinux-base` candidate is:

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

Aurora follows Ubuntu's generic kernel track. `linux-generic` is the supported metapackage for the complete generic kernel **and headers**.

Keeping headers in the standard base is intentional for the first generation because:

- third-party/DKMS modules may need them;
- proprietary-driver workflows may need them;
- they keep the installed kernel/header pair aligned through normal Ubuntu updates.

SupraLINUX must not pin a specific `7.0.0-N` package. The metapackage owns the moving supported kernel version.

## Firmware policy

Ubuntu 26.04 split `linux-firmware` into a metapackage over vendor-specific firmware packages. SupraLINUX uses the full `linux-firmware` metapackage rather than `linux-firmware-minimal` because Aurora targets a general-purpose desktop across diverse hardware.

`firmware-sof-signed` is made explicit even though `linux-firmware` recommends it, because Intel SOF audio firmware is part of the hardware baseline we intend to support rather than an optional image-size optimization.

`wireless-regdb` is explicit because correct wireless regulatory data is part of a complete Wi-Fi platform.

## What is deliberately NOT in `supralinux-base`

- Ubuntu Desktop / GNOME
- `kubuntu-desktop`
- Plasma/KDE
- `snapd`
- server stacks just because Ubuntu Server includes them
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

## Validation gates

Before the base composition is release-frozen, a clean Ubuntu 26.04 build must prove:

1. every dependency resolves from the official Ubuntu 26.04 repositories;
2. `snapd` is absent when `supralinux-snap-policy` is active;
3. the generic kernel boots in BIOS/UEFI test environments as applicable;
4. kernel headers match the installed kernel meta track;
5. firmware packages are present without replacing the full set with `linux-firmware-minimal`;
6. the base can receive normal Ubuntu security/updates without SupraLINUX pinning kernel internals;
7. installing `supralinux-desktop` on top does not require Ubuntu Desktop or Kubuntu metapackages.

This candidate may be reduced or expanded after clean-system evidence, but not for cosmetic package-count goals.
