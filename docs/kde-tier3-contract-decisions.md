# KDE Frameworks Tier 3 package-contract decisions

Status: **PASS — round 3 modeled; KJobWidgets rematerialization pending**

Reviewed: **2026-09-22**

## Authority

KDE upstream 6.30.0 remains the source, feature and dependency authority. SupraLINUX is the packaging authority. Ubuntu Resolute and Debian sid are technical references only.

The reviewed Debian sid trees are used as the packaging baseline because all 20 selected source packages are exact KDE 6.30.0 references whose orig SHA-256 values match KDE authority, and because Ubuntu/Debian expose the same compatibility binary identities for all 20 nodes.

## Global decisions

- initial package version candidate: `6.30.0-0supralinux1`; after Level 0 attempt 1, KIconThemes, KDAV, KWallet, KRunner and KJobWidgets advance to remediation candidate `6.30.0-0supralinux2` because their source packaging changes;
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

These original decisions authorized the first materialization. Level 0 attempt 1 has now built/attempted the 12 Level 0 nodes, but **nothing has been canonically promoted**:

**0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.

Five Level 0 nodes are now in selective source-package remediation. Build execution is paused until those five `-0supralinux2` materializations pass. Stable publication remains subject to explicit user approval.


## Level 0 remediation decisions

Run `35755924197` generated real build evidence and therefore supersedes several assumptions inherited from the technical Debian baseline:

- KIconThemes: remove Debian-only `libkf6configwidgets-dev` from both source Build-Depends and the `libkf6iconthemes-dev` public Depends because upstream exports no KConfigWidgets dependency; restore excluded upstream tests; complete the retained KCoreAddons provider closure.
- KDAV: remove `kio6` and `libkf6kio-dev` because KDE upstream 6.30 does not define a KDAV → KIO build/test dependency.
- KWallet: do not turn upstream's optional KDocTools documentation discovery into a mandatory Build-Depends.
- KJobWidgets: add Resolute `python3-build` for the upstream-enabled Python binding generator.
- KRunner: restore the Debian-QSKIP-suppressed upstream test and mark only the two observed libstdc++ template implementation symbols as optional template instantiations.

These decisions do not weaken KDE tests or invent new KDE dependency edges. They remove distribution-reference assumptions that conflicted with the selected KDE 6.30 semantics.


The five remediation contracts were materialized successfully in run `35759443440`. Their contract revisions remain `6.30.0-0supralinux2`; this closes the source-materialization part of the remediation but does not itself authorize or promote any binary package.


## Level 0 remediation round 2 decisions

Attempt 2, run `35770505868`, narrowed the remaining failures to KIconThemes, KJobWidgets and KWallet. Their source revisions advance to `6.30.0-0supralinux3`.

- KIconThemes keeps the full upstream test set enabled and gains Resolute `qt6-svg-plugins` as a test-environment provider. This supplies the SVG QImage format plugin used by the failing upstream tests; it does not change the KDE dependency DAG.
- KJobWidgets keeps `BUILD_PYTHON_BINDINGS=ON`; `python3-setuptools` is added because the upstream wheel build selects `setuptools.build_meta` under `python -m build --no-isolation`.
- KWallet regains KDocTools only as a **documentation/payload provider**. KDE upstream still treats KDocTools as optional. The already-PASS SupraLINUX KDocTools artifact is injected so the Debian-compatible `kwallet6` payload can include `kwallet-query.1`; no Tier 3 edge is created.

KDAV and KRunner require no further source change: their round-1 remediations passed attempt 2.


## Round 2 materialization result

The three revised source contracts were materialized successfully in run `35806738003` at `6.30.0-0supralinux3`. This proves the source-package transformations and provider adaptations were materializable on Resolute.

It does not prove binary build success. KIconThemes, KJobWidgets and KWallet must still pass the full Level 0 attempt 3. Until that run exists, canonical package state remains pending.


Repository Policy run `35807934729` validated the promoted round-2 contracts. Attempt 3 is now authorized to test those contracts as binary packages; this does not alter the contract decisions themselves.


### Post-promotion validator lifecycle

A completed contract remediation may remain present while the separately validated Level 0 campaign is active. Contract validation therefore distinguishes the source-remediation state from the binary-build authorization state instead of assuming that any active remediation record requires Level 0 to be paused.


## Remediation round 3

Attempt 3 produced **10 workflow SUCCESS / 2 FAIL** with zero canonical promotion.

KJobWidgets retains `BUILD_PYTHON_BINDINGS=ON`, `python3-build` and `python3-setuptools`; those issues are resolved. The remaining failure occurs after a successful build and 3/3 tests because a toolchain-dependent libstdc++ symbol appears as a new symbol. SupraLINUX adds this exact source-template entry:

`(optional)_ZSt19piecewise_construct@Base 6.30.0`

The `optional` tag is a Debian packaging mechanism for private/toolchain-dependent symbols and does not redefine KDE public ABI. KJobWidgets therefore becomes `6.30.0-0supralinux4`.

KWallet has **no source change** in round 3. Its existing optional KDocTools provider contract is retained, while the provider closure gains the already-PASS KArchive artifact because `libkf6doctools-dev 6.30` depends on `libkf6archive-dev >= 6.30`. This remains provider closure and does not become a KDE dependency edge.
