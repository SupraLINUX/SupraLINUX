# KDE Frameworks Tier 3 package-contract decisions

Status: **PASS — materialization authorized**

Reviewed: **2026-09-22**

## Authority

KDE upstream 6.30.0 remains the source, feature and dependency authority. SupraLINUX is the packaging authority. Ubuntu Resolute and Debian sid are technical references only.

The reviewed Debian sid trees are used as the packaging baseline because all 20 selected source packages are exact KDE 6.30.0 references whose orig SHA-256 values match KDE authority, and because Ubuntu/Debian expose the same compatibility binary identities for all 20 nodes.

## Global decisions

- package version candidate: `6.30.0-0supralinux1`;
- preserve all Ubuntu-visible binary package identities;
- Debian 6.30 `debian/` tree is a technical baseline, not authority;
- adapt `debhelper-compat (= 14)` to Resolute-supported level 13;
- target changelog distribution is `resolute`;
- all upstream tests are enabled and failures are fatal;
- distro test suppressions/exclusions are not inherited without node-specific evidence;
- KDE-selected Linux profiles are preserved;
- development dependencies are validated against exported KDE CMake contracts rather than inferred from package coincidence;
- test-only/runtime provider packages do not create false KDE build-DAG edges.

## Upstream feature restorations

KJobWidgets and KXMLGui both declare `BUILD_PYTHON_BINDINGS=ON` in KDE 6.30. Their Debian/Ubuntu packaging disables those bindings, so SupraLINUX restores the upstream default and adds:

- `python3-kf6jobwidgets` → Python module `KJobWidgets`;
- `python3-kf6xmlgui` → Python module `KXmlGui`.

The already-proven Resolute Shiboken/Clang provider adaptation from Tier 2 is reused: `llvm-dev` + `libclang-common-21-dev`. Runtime binding closure uses the supported PySide6 packages; KJobWidgets additionally consumes `python3-kcoreaddons` because its upstream typesystem imports KCoreAddons.

KIO keeps Wayland enabled on Linux and restores `BUILD_TESTING=ON`. KWallet remains the selected Linux password-storage profile and `kwallet6` remains an explicit KIO runtime provider.

Purpose restores `BUILD_TESTING=ON`. Its upstream-required QML modules remain Prison, KItemModels and KCMUtils. KDE Connect integration remains optional: preserve Ubuntu-style `Suggests: kdeconnect` instead of making KDE Connect a default-installed dependency.

## Base integration exception

KDESu upstream defaults to `su`. SupraLINUX intentionally keeps `KDESU_USE_SUDO_DEFAULT=ON` because the Ubuntu-family base locks the root account by default. This is an explicit base-integration adaptation, not an Ubuntu authority decision over KDE.

## State effect

These decisions authorize **materialization only**. No Tier 3 package has been built or promoted:

**0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.

Package builds remain unauthorized until all materialized source packages pass the materialization gate. Stable publication remains subject to explicit user approval.
