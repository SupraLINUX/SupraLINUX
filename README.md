# SupraLINUX

SupraLINUX is a stable, mutable, Ubuntu-compatible Linux distribution built on a minimal Ubuntu 26.04 LTS platform. Its desktop stack follows stable KDE upstream directly.

> **KDE decides what KDE needs. Ubuntu may satisfy that need, but it does not define it.**

## Architecture

Ubuntu 26.04 LTS is the platform authority for the base system: kernel, glibc, systemd, Mesa, firmware, drivers, networking, audio, storage, APT/dpkg and general non-desktop libraries.

KDE upstream is the desktop authority for Plasma, Frameworks, Gear, KWin, Breeze, KDE applications, desktop defaults and desktop dependency requirements.

Qt is selected from the version line required by the selected KDE stable release. Ubuntu may provide Qt when its packages satisfy that profile; otherwise SupraLINUX builds and provides Qt itself.

See:

- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/architecture/build-ci.md`](docs/architecture/build-ci.md)
- [`docs/decisions/ADR-0001-authority-provider.md`](docs/decisions/ADR-0001-authority-provider.md)
- [`docs/status/2026-09-11.md`](docs/status/2026-09-11.md)
- [`manifests/desktop-stack.json`](manifests/desktop-stack.json)

## Current upstream snapshot

The repository manifest records the verified upstream snapshot used by development. As of 2026-09-11 it selects Plasma 6.7.5, KDE Frameworks 6.30.0 and KDE Gear 26.08.1. Plasma 6.7 has an upstream Qt 6.10 dependency profile. Ubuntu 26.04 currently provides Qt 6.10.2, which is recorded as a **reuse candidate**, not as certified until SupraLINUX build and compatibility gates pass.

## CI model

Repository policy checks run on the explicit GitHub-hosted `ubuntu-26.04` label. Authoritative package builds are designed for disposable self-hosted Ubuntu 26.04 VMs using `sbuild`; a hosted runner is not treated as release evidence merely because it has the right OS version.

Build graph state is represented as `PASS`, `FAIL` or `BLOCKED`. `BLOCKED` is never counted as `FAIL`.

## Development state

This project is in architecture/bootstrap development. No document in this repository should be interpreted as evidence that a full KDE stack has already been built or certified unless the corresponding artifacts and CI evidence exist.
