# KDE Frameworks 6.30 — Tier 2 discovery

Status: **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**  
Date: **2026-09-21**

KDE upstream classifies **15** Frameworks in Tier 2 for the current Frameworks API set:

- KAuth
- KColorScheme
- KCompletion
- KContacts
- KCrash
- KDeclarative
- KFileMetaData
- KNotifications
- KPackage
- KPty
- KService
- KStatusNotifierItem
- KUnitConversion
- Syndication
- KMime

Tier 2 may depend on Tier 1 Frameworks. SupraLINUX entered this phase only after the canonical Tier 1 closure at **29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

## Inventory correction

The first Tier 2 discovery incorrectly materialized only KAuth and KMime. That was an inventory error: KDE upstream currently lists 15 Tier 2 Frameworks.

Historically, that correction retained KAuth PASS and expanded the inventory from the incomplete **1 PASS / 1 pending** view to **2 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**. Later package campaigns advanced the canonical state further; the status at the top of this document and the latest section below are authoritative for the current snapshot.

No newly discovered node has been assigned a package version or package PASS/FAIL result. Their source identities and upstream v6.30.0 dependency edges are discovery evidence only until a package contract and real build lane are materialized.

## KAuth — retained PASS

Upstream 6.30.0 SHA-256: `60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9`.

KCoreAddons is always required. For the selected Linux production profile, PolkitQt6-1 is available, so KWindowSystem is also selected and the real Polkit backend is used rather than Fake.

SupraLINUX selects:

- retained KCoreAddons PASS;
- retained KWindowSystem PASS;
- `POLKITQT6-1` auth backend;
- `DBUS` helper backend;
- no silent Fake-backend fallback.

KAuth is **PASS/downstream-eligible** as `6.30.0-0supralinux3`. Retained evidence: run `35497461178`, job `106043001431`, artifact `10601382235`; 6/6 tests, Lintian error gate, ABI/symbols, APT closure, development contract and external consumer all PASS.

## Pending Tier 2 nodes that do not depend on KMime

The other 13 non-KMime pending Frameworks are not blocked by KMime. Their required KDE build edges in upstream `v6.30.0` terminate in retained Tier 1 nodes:

| Framework | Required Tier 1 Framework predecessors |
| --- | --- |
| KColorScheme | KConfig, KGuiAddons, KI18n |
| KCompletion | KCodecs, KConfig, KWidgetsAddons |
| KContacts | KI18n, KConfig, KCodecs |
| KCrash | KCoreAddons |
| KDeclarative | KI18n, KConfig, KGuiAddons |
| KFileMetaData | KI18n |
| KNotifications | KConfig |
| KPackage | KArchive, KI18n, KCoreAddons |
| KPty | KCoreAddons, KI18n |
| KService | KConfig, KCoreAddons, KI18n |
| KStatusNotifierItem | KWindowSystem |
| KUnitConversion | KI18n |
| Syndication | KCodecs |

KDeclarative additionally has conditional KGlobalAccel/KWidgetsAddons surfaces. KFileMetaData has optional/conditional KArchive/KCoreAddons/KConfig/KCodecs surfaces plus several external extractors. Those profiles must be audited before package materialization rather than silently disabling upstream-capable features.

KPackage and KService can optionally use KDocTools; that optional higher-tier documentation edge must not be confused with a required Tier 2 build predecessor.

Provider-audit batch 1 is PASS for **KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication**. Those five are now **package-contract-ready** but remain package-state `pending`; no package build has been attempted for them.

The remaining **8** non-KMime nodes — KColorScheme, KCompletion, KContacts, KDeclarative, KFileMetaData, KPackage, KPty and KService — remain **package-lane-pending** awaiting provider/profile audit. None of the 13 is FAIL or BLOCKED.

## KMime — architecture decision required

Upstream 6.30.0 SHA-256: `2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc`.

Its Tier 1 build predecessor is KCodecs, already retained PASS. The blocker is compatibility architecture, not dependency availability.

Ubuntu Resolute still packages PIM KMime `25.12.3-0ubuntu1` as `libkpim6mime6` / `libkmime-dev`. Frameworks KMime changes the CMake and runtime namespace from `KPim6Mime` / `KPim6::Mime` / `libKPim6Mime.so.6` to `KF6Mime` / `KF6::Mime` / `libKF6Mime.so.6`.

Therefore KMime remains **compatibility-decision-required** under ADR-0002. No package version, Provides/Replaces/Breaks policy or package attempt is authorized before that human decision.

## Authority/provider boundary

KDE upstream defines the Tier 2 inventory, versions, dependencies and feature contracts. Ubuntu 26.04 may provide Qt, Polkit and other general dependencies when they satisfy those requirements. Ubuntu's older KDE packages do not define the SupraLINUX Frameworks version or node set.

## Next non-blocked work

Run the clean-build campaign for the five newly materialized nodes: KColorScheme, KCompletion, KContacts, KPackage and KPty. Each build must consume every required retained Tier 1 PASS predecessor rather than a single representative predecessor.

KDeclarative, KFileMetaData and KService remain package-contract-ready for the following contract/materialization lane. KMime remains independent and decision-gated under ADR-0002; it does not stop the rest of Tier 2.


## KCrash package PASS

KCrash `6.30.0-0supralinux1` is the second retained Tier 2 package PASS. Clean-build run `35535289692`, job `106143242223`, artifact `10613480229` passed 4/4 upstream CTest tests, Lintian error gate, SONAME/export validation, APT runtime closure and external CMake consumer smoke. KCrash is downstream-eligible; the remaining four Batch 2 nodes stay pending.


## Current canonical state — Syndication promoted

Tier 2 is now **3 PASS / 12 pending / 0 current FAIL / 0 BLOCKED**. The retained PASS/downstream-eligible nodes are KAuth, KCrash and Syndication. Syndication `6.30.0-0supralinux1` passed run `35543268413`, job `106164765409`, artifact `10615910224`, after its distribution source was verified as the KDE 6.30 authority content minus exactly the pinned `Files-Excluded` set.

KNotifications, KStatusNotifierItem and KUnitConversion remain pending. Their upstream Python bindings stay enabled. The remaining work is package integration only: explicit PySide6 runtime-provider Depends for the generated Python binary packages, plus one reviewed KStatusNotifierItem symbols adjustment. KMime remains `compatibility-decision-required` under ADR-0002.

Ubuntu Resolute remains provider, not KDE authority. KDE upstream still determines the Framework version and feature profile.


## Batch 2 canonical closure — six Tier 2 PASS

Clean-build run `35544063879` completed PASS for KNotifications `6.30.0-0supralinux1`, KStatusNotifierItem `6.30.0-0supralinux2` and KUnitConversion `6.30.0-0supralinux1`. Together with retained KAuth, KCrash and Syndication, canonical Tier 2 is now **6 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.

All three final Python-binding packages passed clean sbuild, upstream tests, Lintian error policy, ABI/SONAME checks, APT closure, external CMake consumer validation and Python import. KNotifications also passed its QML payload smoke. The PySide6 provider mappings remain packaging/provider integration only; KDE upstream continues to define the enabled binding feature profile.

Remaining pending nodes are KColorscheme, KCompletion, KContacts, KDeclarative, KFileMetadata, KPackage, KPty, KService and KMime. KMime remains blocked only by the explicit compatibility decision in ADR-0002; it is pending, not FAIL or BLOCKED in the build DAG.


## Provider audit batch 2 promoted

KPty, KColorScheme, KCompletion, KContacts and KPackage have passed their Ubuntu Resolute provider/profile audit and advance from `package-lane-pending` to `package-contract-ready`. Canonical package state is unchanged at **6 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.

The remaining unaudited package-lane nodes are KService, KDeclarative and KFileMetadata; KMime remains the separate compatibility-decision case.


## Ordinary provider-audit lane complete

KService, KDeclarative and KFileMetaData passed provider audit batch 3 and are now package-contract-ready. The generated ordinary provider-audit queue is empty.

There are now eight package-contract-ready pending nodes: KColorScheme, KCompletion, KContacts, KDeclarative, KFileMetaData, KPackage, KPty and KService. KMime remains the only pending Tier 2 node outside that lane because ADR-0002 requires a compatibility decision.

Canonical package state remains **6 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.


## Package-contract batch 2 materialized

Run `35608790364` completed **5/5 materialization PASS** for KColorScheme, KCompletion, KContacts, KPackage and KPty. The five remain package-state `pending`, but are now `build-ready`; no clean package build has yet been claimed from this evidence.

The ordinary provider-audit queue remains empty. The generated clean-build queue is exactly these five nodes, while KDeclarative, KFileMetaData and KService remain package-contract-ready. Canonical package state remains **6 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.

## Tier 2 package Batch 3 — multi-predecessor clean-build lane

KColorScheme, KCompletion, KContacts, KPackage and KPty now enter the clean-build lane backed by materialization run `35608790364`. Their package state remains `pending` until real package PASS evidence is promoted.

Batch 3 consumes the complete retained Tier 1 predecessor set for every node and requires the generated `.buildinfo` to prove the exact SupraLINUX development-package revisions. Ubuntu KDE packages are not accepted as substitutes for missing campaign inputs.

To avoid redundant artifact work, ECM plus the seven distinct Tier 1 predecessor artifacts are downloaded and SHA-256/version validated once into a shared retained-input bundle. Five independent package jobs then consume only their declared predecessor subsets. The package matrix remains `fail-fast: false`; shared rootfs/input failures are INFRA rather than replicated package FAILs.

Canonical Tier 2 remains **6 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** until clean-build evidence is promoted. No APT stable promotion is authorized.


## Batch 3 first clean-build campaign — partial closure

Run `35620923130`, attempt 2, validated the new multi-predecessor lane. KCompletion `6.30.0-0supralinux1` and KPty `6.30.0-0supralinux1` are retained **PASS/downstream-eligible**, moving canonical Tier 2 to **8 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**.

KColorScheme never reached `sbuild`: a single SHA-256 value for its already-valid materialized `.debian.tar.xz` had been transcribed incorrectly during promotion. The canonical evidence is corrected; no rematerialization is required.

KContacts reached clean `sbuild` but the Debian 6.30 technical-reference packaging imposed `libkf6coreaddons-dev`, which KDE upstream KContacts 6.30.0 does not require. That technical-reference overconstraint is removed from both source Build-Depends and the development binary Depends. KPackage built its KDE payload but the Debian-reference install list still required manpages produced only by the optional KDocTools integration that SupraLINUX intentionally disabled. Those stale install entries are removed.

Both Debian reference trees also disabled their upstream test invocation. SupraLINUX restores the test commands rather than inheriting those skips. KContacts and KPackage therefore return to fresh deterministic materialization before another package attempt. None of these integration findings is a canonical package FAIL.


## Batch 3 package dependency closure

The second KColorScheme attempt in run `35623204812`, job `106411496226`, reached real `sbuild` and was given back at dependency installation. The authoritative KDE dependency set was already complete: KConfig, KGuiAddons and KI18n. The missing input was instead a **package-level transitive dependency**: retained `libkf6guiaddons-dev 6.30.0-0supralinux2` depends on retained `libkf6coreaddons-dev (>= 6.30.0~)`.

This does **not** add KCoreAddons to KColorScheme's KDE DAG. Batch 3 now records a separate `package_dependency_closure`; KColorScheme has `["kcoreaddons"]`. The runner injects that retained PASS artifact alongside direct predecessors and proves the exact development-package revision in `.buildinfo` and the consumer environment.

The selective replacement materialization run `35623204805` is complete and PASS for KContacts and KPackage. Both are build-ready again. Canonical package state remains **8 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until new clean-build evidence is promoted.


## Current canonical state — KColorScheme and KContacts promoted

Batch 3 remediation run `35627389046` on commit `711827a648046ce3e80d4947234c6bb9ea26c193` promoted two more Tier 2 Frameworks:

- KColorScheme `6.30.0-0supralinux1`: job `106425601911`, artifact `10651864741`, artifact SHA-256 `d52b7bbc99d1e211600f648152781b6dc1b958c51972fdb206099c1e860e88f3`; 2/2 tests, Lintian error gate, SONAME `libKF6ColorScheme.so.6` with 69 exports, APT closure and consumer smoke PASS. Its direct KDE predecessors remain KConfig, KGuiAddons and KI18n; retained KCoreAddons is proven separately as package-level dependency closure and is not a KDE DAG edge.
- KContacts `6.30.0-0supralinux1`: job `106425601953`, artifact `10653450027`, artifact SHA-256 `369ccd7e71ee00120b78d711c5782363996d401703dacd43d57839861a3710e0`; 33/33 tests, Lintian error gate, SONAME `libKF6Contacts.so.6` with 973 exports, QML payload, APT closure and consumer smoke PASS.

Canonical Tier 2 is therefore **10 PASS / 5 pending / 0 current FAIL / 0 BLOCKED**. The ordinary pending nodes are KDeclarative, KFileMetaData, KPackage and KService; KMime remains the independent ADR-0002 compatibility-decision case.

KPackage did not become FAIL. Its second remediation attempt compiled successfully and passed 9/10 upstream tests; the remaining `testpackage-appstream` test failed because AppStream 1.1.2 attempted remote URL reachability checks inside the isolated clean build. AppStream v1.1.2 officially defines `AS_VALIDATE_NONET` as equivalent to `--no-net` for metadata validation. SupraLINUX therefore keeps the KDE test enabled and rematerializes only KPackage with `AS_VALIDATE_NONET=1` scoped to `dh_auto_test`. Structural AppStream validation remains active and KDE feature selection is unchanged.

No package promotion to the stable APT channel is authorized by this state change.


## KPackage ready for isolated retry

The AppStream-offline replacement materialization passed in run `35629129797`, job `106430800639`, artifact `10653266498`. The package remains pending; canonical Tier 2 stays **10 PASS / 5 pending / 0 current FAIL / 0 BLOCKED**.

Only KPackage returns to the clean-build queue. The four other Batch 3 nodes remain retained PASS. The retry keeps the full upstream KDE test suite active and scopes `AS_VALIDATE_NONET=1` only to the test environment.


## Batch 3 closed — KPackage PASS

KPackage `6.30.0-0supralinux1` passed the final isolated retry in run `35631458583`, job `106439193430`, on commit `cfaad11660a827f26092b927645413e7dbf62743`.

Evidence:
- artifact `10653599787`
- artifact SHA-256 `8b55260a3b9f4653c3e5c6589034c1fa96daa5ca000e8669c2a39f8c64288faf`
- shared rootfs artifact `10654945172`, artifact SHA-256 `d92e6869c5e234a99e1577cf9ae231d8c339c9513224736792fce6d874c675e6`
- rootfs content SHA-256 `af1bbbf06929caef42b87b39b26c2b12b7ffdc5c058e747a6fa8eb64be63b2a8`
- **10/10 upstream tests PASS**
- Lintian PASS-errors
- SONAME `libKF6Package.so.6`, 86 exports
- APT runtime closure PASS
- external CMake consumer PASS
- exact retained KArchive `6.30.0-0supralinux4`, KI18n `6.30.0-0supralinux1` and KCoreAddons `6.30.0-0supralinux4` buildinfo proof PASS.

The AppStream adaptation is validated without weakening KDE: `AS_VALIDATE_NONET=1` remains scoped to `dh_auto_test`, and all ten upstream tests execute successfully.

Batch 3 is therefore **5/5 PASS**. Canonical Tier 2 is now **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. The remaining non-decision-gated nodes are KDeclarative, KFileMetaData and KService; KMime remains under ADR-0002. No stable APT promotion is authorized.


## Package-contract batch 3 activated

With Batch 3 clean-build closure complete at **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**, the next ordinary lane is exactly **KDeclarative + KFileMetaData + KService**. KMime remains outside this lane under ADR-0002.

The three nodes already passed provider/profile audit. Their packaging identities are now declared only far enough to capture technical Ubuntu Resolute and Debian sid references:

- KDeclarative: source `kf6-kdeclarative`, candidate `6.30.0-0supralinux1`. KDE v6.30.0 exports CMake package `KF6Declarative` and the C++ library target `KF6::CalendarEvents` with SONAME `libKF6CalendarEvents.so.6`; there is no `KF6::Declarative` library target. The selected Linux profile keeps KGlobalAccel and KWidgetsAddons required as upstream specifies.
- KFileMetaData: source `kf6-kfilemetadata`, candidate `6.30.0-0supralinux1`, target `KF6::FileMetaData`, SONAME `libKF6FileMetaData.so.3`. KArchive and KConfig remain selected optional Framework surfaces; supported external extractors are not silently disabled.
- KService: source `kf6-kservice`, candidate `6.30.0-0supralinux1`, target `KF6::Service`, SONAME `libKF6Service.so.6`. KDocTools is optional upstream and remains deliberately disabled until a matching SupraLINUX provider exists.

State is `reference-capture-pending`. Materialization is fail-closed until current Ubuntu/Debian source records, binary sets, versions and SHA-256 evidence are captured and promoted. Package state remains unchanged.


## Contract batch 3 reference evidence promoted

The KDeclarative/KFileMetaData/KService packaging reference snapshot from run `35633777318` is PASS and pinned. Materialization is authorized for exactly those three nodes.

KDeclarative records a compatibility adaptation: Ubuntu 26.04's `libkquickcontrolsprivate0` binary-package contract is preserved even though Debian 6.30 merged that payload, because KDE 6.30 continues to build the SOVERSION-0 private library. KService retains upstream's optional KDocTools behavior rather than accepting Debian's Build-Depends as authority.

Canonical package state remains **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.


## Contract batch 3 selective rematerialization

The first deterministic materialization run `35635818815` produced three source packages, but artifact inspection identified integration corrections before clean builds.

KFileMetaData is retained build-ready. KDeclarative is rematerialized so the Ubuntu-compatible `libkquickcontrolsprivate0` owns both the SONAME symlink and versioned private library rather than splitting them across two packages. KService is rematerialized so optional KDocTools is absent from both source Build-Depends and `libkf6service-dev` Depends.

These are packaging-integration corrections with `package_attempted=false`; canonical Tier 2 remains **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. KMime remains independently gated by ADR-0002.


## KDeclarative/KFileMetaData/KService build-ready

Contract batch 3 deterministic materialization is now **3/3 PASS**. KDeclarative, KFileMetaData and KService are all build-ready for the next clean package campaign.

The final materialized KDeclarative tree preserves Ubuntu's `libkquickcontrolsprivate0` contract with the complete SOVERSION-0 library payload. KService contains no mandatory KDocTools dependency after applying upstream's optional-provider semantics. KFileMetaData retained its first valid materialization without redundant rebuilding.

Canonical package state is still **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until clean-build evidence promotes these nodes.


## Tier 2 Package Batch 4 — clean build lane

KDeclarative, KFileMetaData and KService are now prepared for a shared-input clean-build campaign.

The lane consumes only retained SupraLINUX PASS Framework artifacts plus Ubuntu Resolute platform dependencies. KDeclarative additionally pins KCoreAddons as a package-level closure input because the retained KGuiAddons development package depends on it. This closure is separate from KDE's upstream Framework DAG and is proven independently in the generated buildinfo.

KDeclarative also carries explicit compatibility gates for Ubuntu's `libkquickcontrolsprivate0`: the binary must be emitted, its private library SONAME must be `libkquickcontrolsprivate.so.0`, exports must be non-empty, and all four KDeclarative QML binary packages must contain their QML metadata payload.

Batch 4 keeps `fail-fast: false`, a shared clean Resolute rootfs and one validated retained-input bundle. Pre-sbuild failures are infrastructure events; BLOCKED remains distinct from FAIL. Canonical Tier 2 remains **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until real package PASS evidence is promoted.


## Batch 4 first campaign — KFileMetaData promoted

KFileMetaData `6.30.0-0supralinux1` is PASS from run `35676553259`: 31/31 upstream tests, ABI, Lintian, APT closure, external consumer and exact retained-predecessor buildinfo proofs all pass. Canonical Tier 2 advances to **12 PASS / 3 pending / 0 current FAIL / 0 BLOCKED**.

KDeclarative's first clean build also compiled and passed its upstream test; its result is classified INFRA because a new post-build ABI checker double-counted a SONAME symlink and target. The checker is repaired and KDeclarative is retried without rematerialization.

KService compiled and passed 7/7 tests but requires a deterministic symbols rematerialization for the Resolute-toolchain-only `std::piecewise_construct` export. The symbol is tagged `optional=toolchain` at version `6.30.0`; no KDE feature or ABI authority is changed.

KMime remains independently decision-gated by ADR-0002.
