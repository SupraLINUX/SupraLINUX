# SupraLINUX architecture overview

Status: **active architecture**  
Last reviewed: **2026-09-27**

## Product definition

SupraLINUX is a stable, mutable, Ubuntu-compatible Linux distribution. Ubuntu 26.04 LTS supplies the platform. SupraLINUX supplies and controls the desktop integration. KDE upstream stable defines the KDE desktop stack.

The governing rule is:

> **KDE decides what KDE needs. SupraLINUX decides the newest compatible integration point. Ubuntu does not select the desktop.**

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

SupraLINUX targets the newest official stable KDE stack that passes the Ubuntu application-compatibility contract. Ubuntu package versions do not select KDE and are not an upper bound. If the next KDE stable release requires a Qt or other platform transition that cannot yet be integrated compatibly, SupraLINUX retains the newest compatible KDE stable release until the compatibility gate can pass.

### Qt authority and provider selection

Qt requires two separate concepts:

1. **Requirement authority:** KDE determines which Qt version line is appropriate for the selected KDE stable release.
2. **Source authority:** the Qt Project defines Qt itself.
3. **Provider:** Ubuntu may provide the required Qt packages. SupraLINUX may provide Qt itself only when that substitution passes the Ubuntu application-compatibility contract.

A provider is not automatically an authority. Failure of Ubuntu's Qt to satisfy a future KDE requirement does not automatically authorize a SupraLINUX Qt replacement; if the replacement cannot be certified compatibly, the KDE integration frontier remains at the newest compatible stable release.

## KDE integration frontier

SupraLINUX, not Ubuntu, selects the desktop stack. The selection objective is:

> **the newest official stable KDE stack that can be fully integrated without breaking the Ubuntu application-compatibility contract.**

This creates a deliberate integration frontier:

- KDE upstream remains authoritative for component relationships, requirements and behavior;
- SupraLINUX owns KDE packaging and desktop integration;
- Ubuntu's KDE package cadence is neither authority nor version ceiling;
- Ubuntu application compatibility is a hard gate on broad platform substitutions such as Qt;
- a newer KDE release is held back when its required platform transition is not yet compatibility-certified;
- beta/RC releases are not canonical unless explicitly approved.

The internal heuristic "stay ahead of Ubuntu where compatible" is an engineering direction, not product marketing. SupraLINUX should describe what it is rather than claim superiority over another distribution.

### Desktop completeness

The selected KDE profile is intended to expose upstream-advertised desktop functionality without requiring users to install missing integration packages after the fact. SupraLINUX therefore packages and installs the dependencies needed for those selected features by default. Exceptions must be explicit and justified, for example by security, legal restrictions, hardware-specific scope, external-service requirements or disproportionate footprint.

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
