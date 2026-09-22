# KDE Frameworks Tier 3 source materialization

Status: **pending CI** as of 2026-09-22.

This gate materializes the 20 canonical KDE Frameworks Tier 3 source packages from the already-approved SupraLINUX package contracts. It does **not** build binary packages and cannot make a Tier 3 node `PASS` or downstream-eligible.

## Authority and baseline

- KDE upstream stable 6.30.0 remains source/feature/default authority.
- The official KDE 6.30 tarball is downloaded independently and verified against the pinned SHA-256 in `manifests/kde-frameworks-tier3.json`.
- Debian sid `6.30.0-1` is only the exact technical packaging baseline. Its `.dsc`, `debian.tar` and orig tar are pinned by SHA-256, and the extracted `debian/` tree must reproduce the promoted tree hash before any adaptation is applied.
- Ubuntu 26.04 Resolute is the platform/provider target, not desktop authority.

The upstream stable directory was rechecked on 2026-09-22; `6.30/` is the newest published stable Frameworks directory: <https://download.kde.org/stable/frameworks/>.

## Deterministic adaptations

The materializer applies only the decisions already recorded in `manifests/kde-tier3-package-contracts.json`:

- replace Debian packaging-tool baseline `debhelper-compat (= 14)` with Resolute-supported `13`;
- target changelog distribution `resolute` and SupraLINUX maintainer metadata;
- remove reference distribution Uploaders/VCS metadata;
- force `BUILD_TESTING=ON` and remove only no-op test suppression;
- preserve/force selected Linux profile flags from KDE upstream;
- select `KDESU_USE_SUDO_DEFAULT=ON` only for the documented Ubuntu-family integration exception;
- retain KIO Wayland/Designer/app-template profile and `kwallet6` runtime provider closure;
- preserve Purpose KDE Connect as optional (`Suggests`), never mandatory;
- materialize the upstream-enabled Python bindings for KJobWidgets and KXMLGui, including their binary package stanzas/install manifests and the verified Resolute PySide6/Shiboken/LLVM build-provider closure.

For KJobWidgets and KXMLGui, Resolute currently provides PySide6/Shiboken 6.10.2 and LLVM 21 provider packages. These are provider facts only; KDE 6.30 remains the feature authority.

## Evidence contract

Each matrix node retains:

- pipeline log and structured `result.json`;
- verified KDE orig tar and SHA-256;
- pre-adaptation Debian packaging-tree hash;
- resulting materialized `debian/` tree and hash;
- `.dsc` and `.debian.tar.*`;
- deterministic complete source-tree tarball;
- adapted `control`/`rules` hashes;
- file-level SHA-256 manifest.

A materialization PASS always records:

- `package_attempted=false`;
- `package_state_effect=none`.

Therefore **materialization PASS is not package PASS**.

## Lifecycle

Current state:

- Tier 3 packages: **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**;
- materialization manifest: `pending-ci`;
- binary builds: **not authorized**;
- stable publication: never automatic and always requires explicit user approval.

After all 20 source materializations pass and their evidence is promoted, the next state is `build-campaign-planning`. Only then is the existing four-level KDE-upstream DAG converted into executable clean-build lanes. Binary package builds remain unauthorized until that build campaign itself is reviewed and activated.
