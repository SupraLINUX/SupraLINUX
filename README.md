# SupraLINUX

SupraLINUX is a stable, mutable, Ubuntu-compatible Linux distribution built on a minimal Ubuntu 26.04 LTS platform. SupraLINUX selects, packages and integrates its own KDE desktop stack instead of inheriting Ubuntu's desktop package cadence.

> **KDE decides what KDE needs. SupraLINUX decides the newest compatible integration point. Ubuntu does not select the desktop.**

## Architecture

Ubuntu 26.04 LTS is the platform authority for the base system: kernel, glibc, systemd, Mesa, firmware, drivers, networking, audio, storage, APT/dpkg and general non-desktop libraries.

KDE upstream is the desktop authority for Plasma, Frameworks, Gear, KWin, Breeze, KDE applications, desktop defaults and desktop dependency requirements.

KDE defines the Qt requirement of each KDE release. The Qt Project defines Qt itself. Ubuntu may provide that Qt when its packages satisfy the selected profile. If a newer KDE release requires a Qt or other platform substitution, SupraLINUX adopts it only after the substitution passes the Ubuntu application-compatibility contract; otherwise SupraLINUX retains the newest stable KDE stack that remains compatible.

See:

- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/architecture/build-ci.md`](docs/architecture/build-ci.md)
- [`docs/runners/ubuntu-26.04.md`](docs/runners/ubuntu-26.04.md)
- [`docs/runners/provisioning.md`](docs/runners/provisioning.md)
- [`docs/decisions/ADR-0001-authority-provider.md`](docs/decisions/ADR-0001-authority-provider.md)
- [`docs/decisions/ADR-0003-kde-integration-frontier.md`](docs/decisions/ADR-0003-kde-integration-frontier.md)
- [`docs/status/2026-09-11.md`](docs/status/2026-09-11.md)
- [`manifests/desktop-stack.json`](manifests/desktop-stack.json)

## Current upstream snapshot

The repository manifest records the verified upstream snapshot used by development. As of 2026-09-27 it selects Plasma 6.7.5, KDE Frameworks 6.30.0 and KDE Gear 26.08.1. Plasma 6.8 is still upstream beta and is therefore not canonical; KDE's schedule assigns Plasma 6.8 a Qt 6.11 dependency profile. Plasma 6.7 uses Qt 6.10, and Ubuntu 26.04 currently provides Qt 6.10.2 as a **reuse candidate**, not as certified until SupraLINUX build and compatibility gates pass.

## Selection policy

SupraLINUX aims for the newest official stable KDE stack that can be shipped **complete** while preserving Ubuntu application compatibility. Ubuntu's KDE package versions are neither the selection authority nor an upper bound. The internal engineering heuristic is to stay ahead of Ubuntu's desktop cadence where compatibility permits; it is not a public comparative claim.

For the selected desktop profile, upstream-advertised KDE features should be available by default rather than requiring users to discover missing distro integration packages. Any exception must be documented and justified by security, legal, hardware-specific, external-service or material footprint constraints.

## CI model

GitHub-hosted `ubuntu-26.04` is a non-authoritative preflight lane. Release-relevant build/test evidence is defined to run inside disposable self-hosted Ubuntu 26.04 **KVM** VMs. Package builds remain isolated through fresh `sbuild/unshare` environments, while system/package tests use `autopkgtest/QEMU` with nested KVM.

Build graph state is represented as `PASS`, `FAIL` or `BLOCKED`. `BLOCKED` is never counted as `FAIL`.

## Development state

This project is in architecture/bootstrap development. The hosted clean-build preflight has real PASS evidence, but the authoritative KVM runner and its QEMU test image are not yet certified. No document should be interpreted as evidence that a full KDE stack has already been built or certified unless the corresponding artifacts and CI evidence exist.
