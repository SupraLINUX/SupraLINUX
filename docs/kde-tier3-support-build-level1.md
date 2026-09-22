# KDE Tier 3 support build level 1

Status: **PASS**

Reviewed: **2026-09-22**

Level 1 contains only **KDED 6.30.0**. It became runnable only after KDocTools reached a real downstream-eligible PASS in support level 0.

## Dependency model

Direct KDE build predecessors are kept separate from package-install closure:

- direct: KConfig, KCoreAddons, KCrash, KDBusAddons, KService, KDocTools;
- package closure needed to install those exact 6.30 artifacts: KArchive and KI18n;
- common build-system root: Extra CMake Modules.

KArchive and KI18n are not promoted to direct KDED dependency edges merely because Debian package relationships require them transitively.

All inputs are retained SupraLINUX PASS artifacts with exact binary-package version and SHA-256 validation before sbuild.

## KDED-specific PASS gates

KDED does not ship a Framework library. The gate therefore does not invent a SONAME contract.

PASS requires:

- clean Resolute sbuild;
- positive non-zero upstream CTest summary;
- exact binary set: `kded6` + `kded6-dev`;
- buildinfo proof for all direct and closure development packages;
- executable ELF validation for `/usr/bin/kded6`;
- payload proof for systemd user service, DBus interface/service, desktop file, logging categories and documentation/manpage;
- proof that no KDED library unexpectedly appears;
- Lintian with no errors;
- installation closure and `apt-get check`;
- `kded6 --version` smoke;
- CMake consumer `find_package(KF6KDED 6.30 REQUIRED)` and live `KDED_DBUS_INTERFACE` path validation.

A KDED PASS closes the three-component support sub-DAG and allows Tier 3 package-contract/build planning to proceed. Stable publication remains gated by explicit user approval.


## Attempt 1 — validation FAIL, package build successful

Run `35702647931`, job `106664471166`, artifact `10683311200`, artifact SHA-256 `1f0cb0ae9609d9c1de732ef3d0c8b7bb80c24b031bc19128c929cc97880fa3ab`.

The actual KDED package build completed successfully in sbuild and the upstream tests passed. The workflow then failed in the external `payload-contract` gate because the validator searched for an uncompressed `kded6.8` path. The generated Debian package correctly installs the manpage as `usr/share/man/man8/kded6.8.gz`.

This is retained as a real historical **FAIL** because the package attempt reached a failing validation gate. It is not a KDED source/package defect.

The remediation changes only the external validation rule to require `kded6.8.gz`. The source package and binary payload do not change, so the retry remains `6.30.0-0supralinux1` rather than creating a meaningless package revision bump.


## Execution-request guard

A runnable level-1 node with `execution_request.status=requested` or `remediation-requested` must execute even when the latest PR commit changes only documentation or integration metadata. The request remains active across `cancel-in-progress` churn and is consumed only when the resulting attempt is promoted into the campaign/attempt ledger.

This prevents a valid initial build or remediation retry from being silently skipped after rapid successive commits.


## Attempt 2 — headless executable-smoke FAIL

Run `35719952518`, job `106720898661`, artifact `10691217831`, artifact SHA-256 `5bd6bd478ec4c0aa58eb6a8042cb9b62ca16818f2bff166d304e9fc4d5c92c72`.

The package again built successfully. The corrected payload gate passed, as did Lintian, package installation and `apt-get check`. The next gate, `executable-smoke`, aborted because `kded6 --version` initializes Qt and the headless GitHub runner had no display for the default `xcb` platform plugin.

The remediation sets `QT_QPA_PLATFORM=offscreen` only for this version smoke. This tests the executable without requiring a graphical session and does not alter KDED packaging or runtime defaults.

Attempt 2 remains a historical **FAIL** at `executable-smoke`. The retry remains `6.30.0-0supralinux1` because no package content changed.


## Attempt 3 — CMake consumer FAIL

Run `35720612123`, job `106722644773`, artifact `10691611217`, artifact SHA-256 `32b194f758467d9a6dcd91971508b6a078c9bb80d2e7f2e52645c6d6580324fc`.

The package build, corrected payload gate, Lintian, package-install closure, `apt-get check`, and the headless `kded6 --version` smoke all passed. The final CMake consumer failed to discover `KF6KDED`.

Inspection of the built `kded6-dev` package proves that `KF6KDEDConfig.cmake` and `KF6KDEDConfigVersion.cmake` are correctly installed under `/usr/lib/x86_64-linux-gnu/cmake/KF6KDED/`. The problem was the test project itself: it declared `project(... NONE)`, so CMake did not initialize the Debian multiarch library architecture search path.

The remediation changes the consumer to `project(... LANGUAGES CXX)`, exercising normal multiarch `find_package(KF6KDED 6.30 REQUIRED)` behavior. The package payload remains unchanged, so the retry remains `6.30.0-0supralinux1`.


## Attempt 4 — PASS

Run `35721085911`, job `106724304390`, artifact `10691372157`, artifact SHA-256 `ff8756cf6efb4746568fa032cfb17cdf5c6b47bc31f532130936536aecb7c5c9`: **PASS**.

The clean Resolute rootfs SHA-256 is `e7d055c5ffe173c81869f89084518c679636e98dba77f868944239625af50ab2`.

Final gates:
- upstream tests: **1/1 PASS**;
- Lintian: **PASS-errors**;
- `apt-get check`: **PASS**;
- executable contract: **PASS** (`kded6 6.30.0`);
- payload contract: **PASS**;
- CMake consumer: **PASS**, resolving `KF6KDED` through normal Debian multiarch discovery and proving `KDED_DBUS_INTERFACE=/usr/share/dbus-1/interfaces/org.kde.kded6.xml`.

Binary SHA-256:
- `kded6_6.30.0-0supralinux1_amd64.deb`: `bb93a73c8f3056405cad73b56b618e7dac58d446104d3178eba91fd51ec4de1a`;
- `kded6-dev_6.30.0-0supralinux1_amd64.deb`: `5242a02a6be2855f98145ee280e6ba58ed9a77268e101ef4268c5f37fe511860`.

Attempts 1–3 remain preserved as historical validation FAILs. Attempt 4 is the single terminal PASS.

The Tier 3 support sub-DAG is now closed: **3 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.
