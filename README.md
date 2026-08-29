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
- Kernel, Mesa, Qt and foundational platform stack: Ubuntu
- KDE/Plasma policy: newest compatible official stable KDE release, rebuilt/integrated by SupraLINUX when qualification justifies overriding Ubuntu's KDE packages
- Current KDE qualification candidate: Plasma/KWin 6.7.4 + KDE Frameworks 6.29.x on Ubuntu 26.04 / Qt 6.10.2; **not yet accepted as the Aurora release stack**
- KDE Gear: separate stable-version review after the Plasma/Frameworks stack is qualified
- Installer: Calamares
- Filesystem default: ext4
- Development model: reproducible, package-driven, monorepo

## Current engineering state

The previous Ubuntu-provided KDE baseline (Plasma 6.6.6 / Frameworks 6.24) produced accepted C1-C3 and C4.0 evidence plus incremental C4.1 evidence. That evidence remains valid as historical version-scoped evidence, but C4.1 is paused while `docs/KDE_STACK_QUALIFICATION.md` evaluates the newer KDE stack. If the candidate stack is adopted, applicable boot/session gates and C4.0 must be rerun before C4 functional certification continues.

## Repository model

Installed systems will use Ubuntu repositories together with SupraLINUX repositories. Ubuntu remains the source of the base system and the overwhelming majority of upstream packages. SupraLINUX repositories carry SupraLINUX-owned packages and intentional, documented overrides/backports, including a qualified KDE stack when required by the accepted KDE release policy.

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
