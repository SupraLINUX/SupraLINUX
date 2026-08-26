# SupraLINUX

> **PRE-ALPHA DEVELOPMENT** — This repository is public for transparent development and CI. There is currently **no supported SupraLINUX release or ISO for end users**.

**Current generation:** SupraLINUX 1.x - Aurora  
**Initial release target:** SupraLINUX 1.0.0 - Aurora  
**Base:** Ubuntu 26.04 LTS

SupraLINUX is a Linux distribution derived from Ubuntu LTS with a KDE Plasma desktop focused first on integration completeness, reliability, and a polished out-of-box experience.

The public repository does not indicate release readiness. Development packages, dependency lists, build logic and documentation may change until the project reaches its release gates.

## First objective

Build the most upstream-like Plasma baseline practical on Ubuntu 26.04 LTS while ensuring that every feature exposed in the shipped desktop has the required backend, dependencies, permissions, integration, and tests.

The first milestone is intentionally not a visual redesign. SupraLINUX-specific applications and deeper visual changes come after the vanilla Plasma baseline is proven complete.

## Core choices

- Base: Ubuntu 26.04 LTS
- Generation codename: Aurora
- Architecture: amd64 initially
- Desktop: KDE Plasma
- Session: Wayland
- Packages: DEB + APT
- Additional application ecosystem: Flatpak
- Snap: blocked by default and not installed by default
- Kernel, Mesa and NVIDIA stack: Ubuntu
- KDE/Plasma packages: Ubuntu repositories
- Installer: Calamares
- Filesystem default: ext4
- Development model: reproducible, package-driven, monorepo

## Repository model

Installed systems will use Ubuntu repositories together with SupraLINUX repositories. Ubuntu remains the source of the base system and the overwhelming majority of upstream packages. SupraLINUX repositories carry SupraLINUX-owned packages and intentional, documented overrides only.

## Project rules

`PROJECT_RULES.md` is the authoritative product and engineering contract for this repository. New architectural, UX, packaging, security, localization, compatibility, recovery, or quality rules must be recorded there when adopted.

## Development branches

- `main`: known-good project state
- `development`: active integration
- `feature/*`: larger isolated work when needed

## Planned layout

```text
SupraLINUX/
├── docs/
├── packages/
├── live/
├── installer/
├── artwork/
├── scripts/
├── tests/
└── .github/
```

The tree will grow only as components become real; empty architecture is not treated as progress.
