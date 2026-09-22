# KDE Tier 2 package contracts

Status: **package-contract batch 2 materialized 5/5; clean build pending**  
Date: **2026-09-21**

The first contract batch contains KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. All five already passed the Ubuntu Resolute provider audit and remain package-state `pending`.

Ubuntu 26.04 and Debian packaging are a **technical reference** only. KDE upstream 6.30.0 defines the actual feature/API contract; SupraLINUX owns the package contract.

Compatibility source/binary names are preserved where Ubuntu already exposes them. KNotifications also preserves the QML split because upstream builds that surface when a QML provider is available.

Upstream 6.30.0 enables Python bindings on Linux for KNotifications, KStatusNotifierItem and KUnitConversion. Ubuntu's current source packages do not expose corresponding Python binary packages, so SupraLINUX must not silently disable the feature. The draft adds:
- `python3-kf6notifications` providing module `KNotifications`;
- `python3-kf6statusnotifieritem` providing module `KStatusNotifierItem`;
- `python3-kf6unitconversion` providing module `KUnitConversion`.

The reference-capture workflow records the current Ubuntu Resolute and Debian sid source records, Build-Depends, binary sets and source-file SHA-256 values. This stage is **not a package PASS** and does not authorize publication.


## Pinned reference evidence

Run `35525532348`, job `106116905607`: **PASS**. Artifact `10609796320`, SHA-256 `0d5d1f961e0189190505545aedca169dc0180ed1d9e189a5eca021267a8385e3`. The normalized snapshot SHA-256 is `5bfdf1238cedc31ccda2a3f3c93459911709b3e7650eb40c129354f42d0286e9`.

Ubuntu Resolute references are `6.24.0-0ubuntu1`; Debian sid references are `6.30.0-1`. Exact `.dsc`, `.debian.tar.xz` and `.orig.tar.xz` SHA-256 values are pinned in the manifest.

Four Debian 6.30 orig tarballs match the KDE upstream source SHA exactly. Syndication does not: Debian's referenced orig SHA is `fb46986bd539f49dc39c79553c4e8e9eaeb5953efa8cba1b47d3b139ee54f5af`, while KDE's official 6.30.0 source SHA is `2d44e45b05766d342d3fe19e92d2b039c916a7a83f9e4dff0f9fa15860e140ee`. SupraLINUX therefore rejects the Debian Syndication orig tarball as a source input and may use only its pinned Debian packaging tree as a technical reference.


### Reference-gate revalidation

After pinning the source-authority mismatch policy, run `35525757861`, job `106117497527`, revalidated the reference capture as **PASS**. Artifact `10610520138`, SHA-256 `987ca77884695296ee6d21a841f428f16ed49fb8b103b84a84db8c735ceac9e9`. Its normalized `snapshot.json` and `versions.tsv` are byte-identical to the initial PASS snapshot, so this second run is the canonical current evidence.


## Resolute packaging-tooling adaptation

The first clean-build Batch 2 run, `35530953084`, exposed a shared provider/tooling incompatibility before any of the four affected Frameworks compiled: Debian's 6.30 technical-reference trees request `debhelper-compat (= 14)`, while Ubuntu 26.04 Resolute provides the debhelper 13 compatibility surface used by the SupraLINUX base.

Because Debian is a technical reference rather than packaging authority, SupraLINUX now normalizes this field to `debhelper-compat (= 13)` during deterministic materialization. The transformation is explicit in the contract manifest and generated materialization metadata. It does not change KDE-selected CMake options, Python bindings, QML surfaces, X11/DBus choices, tests, ABI targets, or any other KDE feature decision.

The prior 5/5 materialization PASS from run `35527533481` remains preserved as historical evidence, but its trees are superseded for build consumption. The five package contracts return temporarily to `package-contract-ready` until CI produces and pins replacement source trees. This transition does not alter package state: all five remain `pending`.


### Provider-adapted materialization evidence

Run `35534384634` on commit `f2927e550d113369a33011d7737136a0bb91f272` completed **PASS for all five nodes**. Every generated `debian/control` passed the explicit `debhelper-compat (= 13)` tree contract while preserving the KDE-selected feature profile. Exact artifact, full-tree, Debian-tree, `.dsc`, generated `.debian.tar.xz` and authoritative orig SHA-256 values are pinned in `manifests/kde-tier2-package-contracts.json`.

This supersedes the old materialized trees for build consumption. It remains a materialization/readiness PASS, not a package PASS.


## Batch 2 provider/integration remediation

Clean-build run `35534595946` exposed two additional packaging/provider requirements after the debhelper compatibility adaptation had succeeded.

The generated SupraLINUX changelog must name the Ubuntu base release target, so deterministic materialization now writes `resolute` instead of `UNRELEASED`. This is a release-target integration choice, not a KDE feature choice.

For the three upstream Python-binding nodes, Shiboken's generator must be able to discover the matching Clang resource/include surface. Resolute's `libshiboken6-dev` installation did not by itself make `llvm-config` available in the clean build. SupraLINUX therefore adds the Resolute `llvm-dev` provider for KNotifications, KStatusNotifierItem and KUnitConversion. This preserves `BUILD_PYTHON_BINDINGS=ON`; it does not weaken or replace KDE upstream defaults.

Both adaptations are machine-readable under `provider_adaptations.ubuntu-resolute` and require fresh deterministic materialization plus clean-build validation. The previous materialization remains historical evidence and is no longer build-consumable.


### Corrected materialization evidence

Run `35535155799` on commit `e03516fab151d3ea5ec6443ad65d5c4961aa6e68` completed **5/5 PASS** with the Resolute changelog target and Shiboken LLVM provider encoded in the generated trees. This materialization supersedes run `35534384634` for build consumption; both remain historical evidence.

The package state is unchanged. KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication are again `build-ready` but remain `pending` until a real clean-build PASS satisfies the complete Batch 2 gates.


## Partial PASS and distribution-source repack

KCrash is now a retained package PASS and is excluded from later materialization targets. Package-contract materialization may therefore be partial: only pending nodes whose previous generated tree was invalidated are regenerated.

Syndication keeps KDE Frameworks 6.30.0 as source/version authority, but its distributable orig requires a verified `Files-Excluded` repack. The pinned Debian orig is accepted only if CI proves its extracted contents equal KDE's official source minus exactly the paths declared by the pinned Debian copyright metadata. Debian remains a technical reference/provider, not the authority over Syndication.


## Python binding runtime-provider contracts and KStatus symbols revision

Clean-build run `35543268413` proved that build-time Shiboken/Clang closure is now correct: all three Python bindings generated successfully. It also exposed the separate runtime-provider contract of the generated Python packages.

The package contracts now retain the upstream PySide typesystem basis and the minimal Ubuntu Resolute provider closure:

- KNotifications loads QtGui → `python3-pyside6.qtgui` (which depends on QtCore).
- KUnitConversion loads QtCore → `python3-pyside6.qtcore`.
- KStatusNotifierItem loads QtCore + QtGui + QtWidgets → `python3-pyside6.qtwidgets` (which depends on QtGui and QtCore).

These dependencies are provider mappings for KDE-selected bindings; they do not make Ubuntu authoritative over the feature profile.

KStatusNotifierItem also has one reviewed symbols overlay after its real package FAIL: `_ZSt19piecewise_construct@Base` is recorded as `optional=templinst` at upstream floor `6.30.0`. The previous build let `dpkg-gensymbols` add the current Debian revision automatically, which Lintian correctly rejects. Its next package candidate is therefore `6.30.0-0supralinux2`.

Syndication is no longer a pending materialization target: its verified distribution repack passed the full clean package gate and is retained as package PASS. Current rematerialization targets are only KNotifications, KStatusNotifierItem and KUnitConversion.


### Runtime/symbol remediation materialized

Run `35543959765` produced PASS materializations for all three pending Python nodes. The materialized contract now pins KNotifications' QtGui provider, KUnitConversion's QtCore provider and KStatusNotifierItem's QtWidgets provider. KStatusNotifierItem is revision `6.30.0-0supralinux2` and the exact reviewed `_ZSt19piecewise_construct@Base 6.30.0` optional entry is part of its deterministic Debian tree.

This is still package-contract readiness, not package PASS. Clean package validation remains mandatory.


## Batch 2 runtime contracts validated by clean packages

Run `35544063879` validated the previously materialized PySide6 runtime-provider contracts in real clean packages: KNotifications imports successfully with the QtGui provider, KStatusNotifierItem with QtWidgets, and KUnitConversion with QtCore. KStatusNotifierItem's reviewed optional template-symbol entry also passed Lintian and ABI validation in revision `6.30.0-0supralinux2`.

The materialization contracts remain reproducibility inputs; the package PASS authority is the clean-build evidence retained in the Batch 2 campaign and canonical Tier 2 manifest.


## Tier 2 package-contract batch 2 activated

The active contract batch is KColorScheme, KCompletion, KContacts, KPackage and KPty. All five already passed provider audit and are package-contract-ready.

Ubuntu Resolute remains only a compatibility/packaging reference. The current Ubuntu 26.04 source package names and binary compatibility surfaces are recorded, but KDE 6.30.0 remains source/feature authority. Debian sid is used only to capture the matching 6.30 packaging tree.

The previous KCrash/KNotifications/KStatusNotifierItem/KUnitConversion/Syndication contract evidence and materialization history is retained under the manifest history and canonical package evidence; it is not overwritten by the new active batch.

Materialization is explicitly blocked while the new technical-reference snapshot is pending.


## Package-contract batch 2 reference capture PASS

Run `35607692121`, job `106358716421`, artifact `10642218003`, artifact SHA-256 `d683cade7450654d599e467486f0956632044bedbfc880fdc92ece091add61fe`: **PASS** for KColorScheme, KCompletion, KContacts, KPackage and KPty.

Ubuntu Resolute references are `6.24.0-0ubuntu1`; Debian sid references are `6.30.0-1`. The Debian orig tarballs for all five match the KDE-authoritative 6.30.0 source SHA-256 values, so no source repack policy is required for this batch.

KPackage exposes a deliberate authority/provider split. KDE upstream declares KF6DocTools optional, while the Debian technical-reference packaging makes `libkf6doctools-dev` mandatory. SupraLINUX removes that technical-reference Build-Depends and materializes `-DCMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` until a matching SupraLINUX KDE 6.30 DocTools provider exists. This avoids importing an older distro KDE Framework solely because the reference packaging chose it.

Reference snapshot SHA-256 is `703ec8233c2694bad11b9b41545bc5828f45b8e070706bac35a470c7d7af139a`; versions TSV SHA-256 is `5b135cfaedd0b6a4d1d2bbd6648a943fb351e54f9d2294114b75ef99c2d2c861`.


## Package-contract batch 2 materialization promoted

Materialization run `35608790364` is the retained PASS for KColorScheme, KCompletion, KContacts, KPackage and KPty. Exact artifact, full-tree, Debian-tree, `.dsc`, `.debian.tar.xz` and authoritative orig SHA-256 values are now canonical in `manifests/kde-tier2-package-contracts.json`.

The contract state is now `materialized`; all five canonical nodes are `build-ready` while their package state remains `pending`. The generated Tier 2 plan therefore moves these five nodes from `package_contract_ready` to `build_queue`. KDeclarative, KFileMetaData and KService remain package-contract-ready for a later contract batch, and KMime remains decision-gated by ADR-0002.

This promotion does not rerun or supersede the already-PASS provider/reference lanes and does not authorize publication to `stable`.


## Batch 3 feedback — selective contract remediation

Clean-build run `35620923130` proved two Debian-reference assumptions that SupraLINUX must not inherit.

KContacts 6.30.0 authoritative CMake requires KF6 I18n, Config and Codecs and contains no KCoreAddons dependency. The Debian 6.30 reference nevertheless adds `libkf6coreaddons-dev` to source Build-Depends and `libkf6contacts-dev` Depends. Both reference-only overconstraints are removed during materialization.

KPackage's optional KDocTools integration remains disabled until a matching SupraLINUX provider exists. The Debian reference's `kpackagetool6.install` still requested two manpage paths generated only by KDocTools, so those stale payload entries are removed as part of the same explicit adaptation.

The Debian reference also disables `dh_auto_test` for both KContacts and KPackage. SupraLINUX restores those test invocations because reference-distribution test skips are not authoritative over KDE's selected `BUILD_TESTING=ON` profile.

Only KContacts and KPackage require replacement materialization. KColorScheme's tree remains valid; only a promoted hash transcription is corrected. KCompletion and KPty are now package PASS.


## Package closure is not KDE dependency authority

Batch 3 distinguishes two dependency classes explicitly:

- `predecessors`: KDE Framework dependencies determined by authoritative KDE upstream CMake.
- `package_dependency_closure`: transitive Debian/SupraLINUX package contracts needed to install those retained predecessor development packages.

The distinction was required by KColorScheme: upstream requires KGuiAddons but not KCoreAddons, while SupraLINUX `libkf6guiaddons-dev` correctly carries a package dependency on `libkf6coreaddons-dev`. The resulting KCoreAddons input is therefore package closure only and must never be promoted into the KDE DAG.

Both classes must come from retained PASS artifacts. When package closure is non-empty, its development-package version is separately proven in `.buildinfo` and in the post-build consumer environment.


## KPackage AppStream offline validation contract

Batch 3 run `35627389046` established that KPackage's restored upstream tests are functional: 9/10 passed, while `testpackage-appstream` failed only on AppStream remote URL reachability in the isolated build. The provider observed in Ubuntu Resolute is `appstream 1.1.2-1`.

AppStream v1.1.2 is the authority for this validator behavior. Its manual explicitly defines `--no-net` as “do not access the network when validating metadata” and states that `AS_VALIDATE_NONET` has the same effect. SupraLINUX therefore records an explicit provider/test-environment adaptation:

- tool: `appstreamcli`
- provider: Ubuntu Resolute `1.1.2-1`
- setting: `AS_VALIDATE_NONET=1`
- scope: `dh_auto_test` only
- KDE feature effect: none
- upstream AppStream reference: `https://github.com/ximion/appstream/blob/v1.1.2/docs/xml/man/appstreamcli.1.xml`.

The KPackage upstream test is not deleted, filtered or marked flaky. The full test suite remains mandatory. Only external URL reachability is removed from the isolated build contract. Any structural AppStream error or other KDE test failure still fails the package attempt.


## Package-contract batch 2 fully validated

Final KPackage run `35631458583`, job `106439193430`, validated the AppStream offline test-environment contract in a real clean package build: **10/10 upstream tests PASS**, Lintian, ABI, APT closure and external consumer all PASS.

All five package-contract batch 2 nodes are now retained package PASS:
KColorScheme, KCompletion, KContacts, KPackage and KPty.

The next ordinary package-contract-ready set is KDeclarative, KFileMetaData and KService. KMime remains outside that lane under ADR-0002. No stable promotion is authorized by package PASS alone.


## Package-contract batch 3 — reference capture gate

Active selected nodes are KDeclarative, KFileMetaData and KService. Their source authority remains KDE Frameworks 6.30.0. Ubuntu Resolute and Debian sid are technical packaging references only.

The declared Ubuntu-compatible binary surfaces are:

- KDeclarative: `libkf6calendarevents6`, `libkf6declarative-data`, `libkf6declarative-dev`, `libkf6declarative-doc`, `libkquickcontrolsprivate0`, and the four QML modules `org-kde-draganddrop`, `graphicaleffects`, `kquickcontrols`, `kquickcontrolsaddons`.
- KFileMetaData: `libkf6filemetadata-bin`, `-data`, `-dev`, `-dev-tools`, `-doc`, and ABI package `libkf6filemetadata3`.
- KService: `libkf6service-bin`, `-data`, `-dev`, `-doc`, and `libkf6service6`.

No Debian tree or Ubuntu tree is accepted yet. The contract-reference workflow must capture and hash current source records first. Until that PASS is promoted, deterministic materialization is blocked and `package_attempted=false`.


## Contract batch 3 reference capture PASS

Reference run `35633777318`, job `106446066768`, artifact `10655657085` completed PASS. Artifact SHA-256 is `14cc5e7684149844cd39df66bd0f69d7415428c4a4e2b194dbe7505c181f5fe4`; normalized snapshot SHA-256 is `398da3131d1711d8401a75c915b2958c2469b74e89d23a638031a678304f6652`.

All three technical references resolve to Ubuntu Resolute `6.24.0-0ubuntu1` and Debian sid `6.30.0-1`. Debian 6.30 upstream orig tarballs exactly match the KDE-authority SHA-256 for KDeclarative, KFileMetaData and KService.

KDeclarative preserves Ubuntu 26.04's separate `libkquickcontrolsprivate0` runtime package. Debian 6.30 no longer lists that binary package, but KDE v6.30.0 still builds and installs `kquickcontrolsprivate` with SOVERSION 0. SupraLINUX therefore splits that library back into the Ubuntu-compatible package without changing the KDE feature profile.

KService continues to disable optional KDocTools until a matching SupraLINUX provider exists. Because upstream only adds documentation/manpages when `KF6DocTools_FOUND`, the Debian-reference KDocTools Build-Depends and only the corresponding `kbuildsycoca6.8` manpage install entries are removed.


## Contract batch 3 integration feedback

Inspection of materialization run `35635818815` refined two package contracts without changing KDE authority.

**KDeclarative:** Ubuntu's `libkquickcontrolsprivate0` contract represents the complete SOVERSION-0 runtime library. KDE 6.30 installs both `libkquickcontrolsprivate.so.0` and the versioned `libkquickcontrolsprivate.so.6.30.0`. The SupraLINUX split therefore owns both entries. The QML package keeps only QML/plugin payload and must not duplicate either library entry.

**KService:** KDocTools is optional upstream. Removing it only from source Build-Depends was insufficient because the Debian technical reference also propagated `libkf6doctools-dev` into `libkf6service-dev` Depends. SupraLINUX removes that binary Depends as the same optional-provider overconstraint.

KFileMetaData's first materialization needs no remediation and remains retained PASS materialization evidence. No package state changes occur during these corrections.


## Contract batch 3 materialization contract validated

The corrected KDeclarative and KService trees passed deterministic rematerialization in run `35636800957`. Together with retained KFileMetaData, the contract batch is now 3/3 materialized.

The KDeclarative binary split is now fail-closed for the complete private-library runtime payload: both SONAME symlink and versioned library must move together, and neither may remain duplicated in another binary package install list.

KService's optional KDocTools adaptation is complete across both source and development binary dependency contracts. This preserves upstream's optional dependency semantics while keeping Ubuntu/Debian package compatibility where technically applicable.


## KService Resolute toolchain-symbol adaptation

Batch 4 run `35676553259` showed that the Resolute C++ toolchain exports `_ZSt19piecewise_construct@Base` from `libKF6Service.so.6`. The symbol is absent from the pinned Debian 6.30 symbols baseline, causing `dpkg-gensymbols` to assign `6.30.0-0supralinux1` and Lintian to reject a current-version-with-Debian-revision symbol.

This is recorded as a toolchain integration adaptation, not an upstream KDE API addition:

- file: `libkf6service6.symbols`
- symbol: `_ZSt19piecewise_construct@Base`
- tag: `optional=toolchain`
- minimum version: `6.30.0`
- KDE feature effect: none.

The existing KDocTools optional-provider adaptation is unchanged. A fresh KService materialization and clean build are required before PASS.


## KService toolchain-symbol adaptation validated

The KService adaptation was validated by the final clean package build in run `35681046106`:
- 7/7 upstream tests PASS;
- Lintian PASS-errors;
- `libKF6Service.so.6` with 299 exports;
- exact retained Framework buildinfo proof PASS;
- APT and consumer smoke PASS.

The selected `optional=toolchain` entry therefore remains the canonical SupraLINUX symbols treatment for `std::piecewise_construct` on the Resolute toolchain. It does not change KDE feature selection or upstream API authority.


## Package-contract batch 4 — KMime

ADR-0002 is accepted and provider audit batch 4 is PASS. The active package-contract batch now contains only **KMime**.

Authority and outputs:

- KDE authority source: `kmime-6.30.0`;
- SupraLINUX source-package identity: `kf6-kmime`;
- candidate: `6.30.0-0supralinux1`;
- target binaries: `libkf6mime-data`, `libkf6mime-dev`, `libkf6mime6`;
- CMake: `KF6Mime` / `KF6::Mime`;
- ABI target: `libKF6Mime.so.6`.

Reference capture is intentionally split:

- Ubuntu Resolute: source `kmime` from the legacy PIM line, expected `libkmime-data`, `libkmime-dev`, `libkpim6mime6`;
- Debian sid: source `kf6-kmime` from Frameworks 6.30, expected `libkf6mime-data`, `libkf6mime-dev`, `libkf6mime6`.

The Ubuntu version line is allowed to differ because it is a **legacy compatibility contract**, not the selected KDE source. This exception is explicit and node-local; normal Tier 2 reference captures retain the selected-KDE upper-bound rule.

No fake `Provides/Replaces`, SONAME shim, or ABI equivalence is authorized. Materialization remains blocked until reference capture passes.
