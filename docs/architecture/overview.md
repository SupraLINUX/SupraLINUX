# SupraLINUX architecture overview

Status: **active architecture**  
Last reviewed: **2026-09-11**

## Product definition

SupraLINUX is a stable, mutable, Ubuntu-compatible Linux distribution. Ubuntu 26.04 LTS supplies the platform. SupraLINUX supplies and controls the desktop integration. KDE upstream stable defines the KDE desktop stack.

The governing rule is:

> **KDE decides what KDE needs. Ubuntu may satisfy that need, but it does not define it.**

SupraLINUX is not Ubuntu Desktop with modifications, Kubuntu with newer packages, KDE neon with different branding, an Arch derivative, or an immutable/image-based operating system.

## Authority boundaries

### Ubuntu authority

Ubuntu 26.04 LTS remains the primary authority and provider for the platform layer:

- Linux kernel and hardware enablement;
- glibc and base runtime;
- systemd, udev and boot plumbing;
- Mesa, DRM-facing user-space components, firmware and drivers;
- networking and NetworkManager;
- PipeWire/ALSA and Bluetooth platform integration;
- storage and general system libraries;
- OpenSSL and platform security maintenance;
- APT and dpkg;
- the compatibility baseline for Ubuntu-targeted software.

### KDE upstream authority

KDE upstream is authoritative for:

- KDE Plasma;
- KDE Frameworks;
- KDE Gear;
- KWin;
- Plasma Workspace;
- Breeze;
- KDE applications;
- KDE desktop defaults and component relationships;
- KDE build requirements and the Qt version line agreed for a Plasma feature release.

SupraLINUX follows the newest official stable KDE releases. Ubuntu package versions are not a reason to retain an older KDE release.

### Qt authority and provider selection

Qt requires two separate concepts:

1. **Requirement authority:** KDE determines which Qt version line is appropriate for the selected KDE stable release.
2. **Source authority:** the Qt Project defines Qt itself.
3. **Provider:** Ubuntu may provide the required Qt packages. If Ubuntu cannot satisfy the selected profile, SupraLINUX becomes the package provider.

A provider is not automatically an authority.

## Mutable Debian-package system

SupraLINUX keeps a conventional mutable system:

- `.deb` packages;
- APT repositories;
- dpkg package state;
- mutable `/usr`;
- mutable `/etc`.

Recovery is intended to be implemented with Btrfs snapshots, Snapper, APT hooks and a recovery environment rather than by replacing the package model with an immutable image model.

## Package precedence

SupraLINUX-built KDE packages must take precedence over equivalent Ubuntu packages when SupraLINUX owns that component. Debian and Ubuntu packaging can be used as technical reference material, but neither defines the selected KDE stack.

When SupraLINUX replaces Qt or another broadly consumed library, compatibility with Ubuntu software becomes an explicit gate. Package names, dependency relationships, `Provides`, `Replaces`, `Breaks`, ABI, Multi-Arch and shlibs/symbols metadata must be evaluated rather than assumed.

## Current selection model

The current machine-readable selection is in `manifests/desktop-stack.json`. Version numbers in prose are informational; automation should consume the manifest.

A selected provider remains a **candidate** until build, runtime and compatibility evidence exists. This rule prevents documentation from claiming certification based only on matching version numbers.
