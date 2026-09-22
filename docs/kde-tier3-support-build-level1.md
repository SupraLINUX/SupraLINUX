# KDE Tier 3 support build level 1

Status: **pending CI**

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
