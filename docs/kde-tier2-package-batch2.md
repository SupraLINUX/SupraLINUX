# KDE Frameworks Tier 2 — package Batch 2

Status: **replacement materialization PASS; clean-build remediation queued**  
Date: **2026-09-20**

Batch 2 covers KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. The five nodes remain package-state `pending`; canonical Tier 2 is still **1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED**.

Run `35530953084` was the first real clean-build campaign. KCrash, KNotifications, KStatusNotifierItem and Syndication crossed the `sbuild` boundary but all converged at `install-deps` on the same unsatisfied `debhelper-compat (= 14)` requirement inherited from the Debian 6.30 technical-reference packaging. This is recorded as a real execution with result **INFRA**, not four node-owned package FAILs.

KUnitConversion did not reach `sbuild`: retained KI18n validation found a single incorrectly transcribed SHA-256 for `libkf6i18n-data`. The campaign pin is corrected to the hash verified from the retained PASS artifact. That incident is pre-attempt INFRA.

Ubuntu Resolute is the provider for packaging tooling. The active provider exposes debhelper compatibility level 13, while the Debian 6.30 reference tree requests 14. SupraLINUX therefore applies an explicit packaging-tooling adaptation from compatibility level 14 to 13 during deterministic materialization. This adaptation has **no KDE feature-profile effect**: KDE upstream still defines the selected CMake/features contract.

The old materialization PASS is preserved as historical evidence but is no longer build-consumable. Until the five trees are regenerated and pinned, the generated build queue is empty and Batch 2 package jobs are intentionally skipped.

A real package attempt begins immediately before clean `sbuild`. Crossing that boundary records a real execution, but it does **not** automatically make the result a canonical FAIL. Post-boundary failures require root-cause classification; **FAIL requires a node-owned cause**. Shared infrastructure/provider failures retain package-state effect `none`.

The matrix remains **fail-fast: false**. PASS still requires non-zero upstream CTest success, exact binary set, Lintian error gate, expected SONAME, APT runtime closure and an external CMake consumer, plus Python/QML smoke where applicable.

No Batch 2 result publishes automatically. PASS may later be evaluated for `testing`; promotion to `stable` requires explicit user approval.


## Replacement materialization PASS

Materialization run `35534384634` completed **5/5 PASS** using the explicit Resolute `debhelper-compat 14 -> 13` packaging-tooling adaptation. The generated tree/debian-tree/source-package hashes and artifact digests are pinned in the package-contract and Batch 2 campaign manifests.

The five nodes return to `build-ready`; Batch 2 resumes as `remediation-pending-build` with `fail-fast: false`. The corrected KI18n predecessor hash is part of the campaign input.

Raw runner evidence now uses `ATTEMPT_FAILURE` for a post-`sbuild` failure until root-cause classification is complete. Only a node-owned cause may be promoted to canonical `FAIL`.


## Clean-build remediation attempt — run 35534595946

The campaign used one **shared Resolute rootfs**, artifact `10612413376`, SHA-256 `6f983685852266dbe08e4401cb9a1ec2cf1804b403ab97b916db43732f8d3a8c`. All five jobs crossed the clean-`sbuild` boundary, so their evidence records `package_attempted=true`; root-cause classification remains separate from canonical package state.

Two shared integration causes were identified:

- KCrash and Syndication compiled and emitted binary packages, then failed the Lintian error gate because the generated SupraLINUX changelog used distribution `UNRELEASED`. The materializer now targets `resolute`.
- KNotifications, KStatusNotifierItem and KUnitConversion preserved KDE's `BUILD_PYTHON_BINDINGS=ON`, but Shiboken ApiExtractor could not locate Clang's built-in include directory and reported the absence of `llvm-config`; parsing then failed at `cstddef -> stddef.h`. Their materialized Build-Depends now add the Ubuntu Resolute `llvm-dev` provider, which supplies the default LLVM toolchain surface and `/usr/bin/llvm-config`.

Both are classified **INFRA / shared integration-provider causes**, with `package_state_effect=none`. None of the five becomes canonical FAIL. The current materialized trees are superseded for build consumption until the corrected deterministic rematerialization is PASS and pinned.


## Second corrected materialization PASS

Run `35535155799` completed **5/5 PASS** after applying both shared remediations: changelog distribution `resolute` and the `llvm-dev` provider for the three Shiboken/Python-binding nodes. Exact artifact and source-tree hashes are pinned in the contracts and campaign manifests.

The five package nodes return to `build-ready`; Batch 2 is again `remediation-pending-build`. The next campaign must use the corrected materialization and retain `fail-fast: false`.


## Partial promotion after run 35535289692

KCrash `6.30.0-0supralinux1` is now **PASS/downstream-eligible**: run `35535289692`, job `106143242223`, artifact `10613480229`, artifact SHA-256 `1f97e3cbcba2ed1d6b33af69cae1920726c2d5efab2382c3b21083a2e29d30d9`, rootfs content SHA-256 `db01172d5e4e9cadebf1dbfd0c7f631710e981f051160edb0a923b8613399e8f`, **4/4 tests PASS**, Lintian PASS-errors, SONAME `libKF6Crash.so.6`, 13 exports, APT closure PASS and consumer smoke PASS.

The other four jobs are not canonical FAILs. KNotifications, KStatusNotifierItem and KUnitConversion share a Shiboken/Clang resource-header provider gap. Syndication builds and passes 4/4 tests but requires a distribution source repack matching its declared `Files-Excluded`. They are removed from the build queue until corrected materializations exist.

The Batch remains `fail-fast: false`; `package_attempted=true` evidence is retained for every real execution. Promotion to `stable` still requires explicit user approval.


## Four-node remediation campaign — partial PASS and three-node isolation

Run `35543268413` used shared Resolute rootfs artifact `10615518322` (artifact SHA-256 `bb95b71c2b572183e86f5c7d4b9364f5d270cb92fe3332ababc378ed0d693058`; rootfs content SHA-256 `0943ab94eb5f4d0cbbf64bb0d69ccf36ad48309cbafc1c73e8745d3925a4b734`). All four package jobs had `package_attempted=true`; `fail-fast: false` remained in force.

**Syndication PASS:** job `106164765409`, artifact `10615910224`, SHA-256 `729dc8301377ba6e7d0a29cf65552542e0df85d76b19a24270bd328be13c9d7c`. It passed 4/4 tests, Lintian errors gate, SONAME/ABI validation, APT closure and external consumer smoke. The verified `Files-Excluded` repack is therefore validated by a real clean build and Syndication is retained PASS/downstream-eligible.

KNotifications and KUnitConversion built successfully, passed tests, Lintian, APT closure and the external C++ consumer, then failed only at Python import because their generated Python packages lacked the PySide6 module packages loaded by the KDE upstream binding typesystems. The package contract now maps those upstream typesystems to minimal Resolute providers: KNotifications → `python3-pyside6.qtgui`; KUnitConversion → `python3-pyside6.qtcore`.

KStatusNotifierItem built its Python binding and passed 1/1 tests, then failed its Lintian gate because `dpkg-gensymbols` auto-added `_ZSt19piecewise_construct@Base` with the full Debian revision. This is retained as a node-owned historical package FAIL. Candidate revision `6.30.0-0supralinux2` records the reviewed export as `optional=templinst` with upstream version floor `6.30.0`; Lintian requires Debian revisions to be stripped from symbols versions.

KStatusNotifierItem's upstream binding loads QtCore, QtGui and QtWidgets typesystems. Its minimal Resolute runtime provider is `python3-pyside6.qtwidgets`, which already depends on the QtGui and QtCore PySide6 packages.

The next materialization/build cycle contains only KNotifications, KStatusNotifierItem and KUnitConversion. KCrash and Syndication are retained PASS and excluded. No promotion to `stable` is authorized.


## Three-node corrected materialization PASS

Materialization run `35543959765` on commit `4cf3d9f9e6f28ac6f759b3c2d9ca75c4698d6e09` completed **3/3 PASS** for KNotifications, KStatusNotifierItem and KUnitConversion. KCrash and Syndication were correctly excluded as retained package PASS nodes.

- KNotifications: artifact `10616275343`, SHA-256 `5dc140d99a91bdd0ccd3ed3564f5d336a6b820acd57dd2317f8c7a5cbf3f1d15`.
- KStatusNotifierItem `6.30.0-0supralinux2`: artifact `10615805884`, SHA-256 `866f5c704761061d7199c9dcc0edf1c56667c32f65cacfb0ee7320527a131862`.
- KUnitConversion: artifact `10615638692`, SHA-256 `e9578b08cd2fa5ecd98b3b84e4bd80cc1031118da71929597a0179648277e1a4`.

The generated trees enforce the explicit PySide6 runtime-provider Depends; KStatusNotifierItem additionally contains the reviewed `optional=templinst` symbols entry. These three nodes return to `build-ready`; the next clean-build matrix contains exactly these three.


## Batch 2 final clean-build closure — 5/5 PASS

Run `35544063879` on commit `3636723999d604e5110621fc13d7aed778ec2d51` completed **SUCCESS** with one shared Resolute rootfs and exactly the three remaining package jobs. Retained KCrash and Syndication were not rebuilt.

KNotifications `6.30.0-0supralinux1`: job `106166898618`, artifact `10616445435`, artifact SHA-256 `09ede9c6f1f07333e1ea54291232a855c6dca9f9cf9679a38d37b1ec69eb6135`; 1/1 tests, Lintian PASS-errors, 162 ABI exports, APT closure, consumer smoke, Python import and QML payload smoke all PASS.

KStatusNotifierItem `6.30.0-0supralinux2`: job `106166898613`, artifact `10616011544`, artifact SHA-256 `542bebf07f51d20c0dccf21c06123418e025e8904b1864bd21692c9af0cfe552`; 1/1 tests, Lintian PASS-errors, 113 ABI exports, APT closure, consumer smoke and Python import all PASS. The historical revision-`-1` symbols FAIL remains preserved in the attempts ledger.

KUnitConversion `6.30.0-0supralinux1`: job `106166898551`, artifact `10616255861`, artifact SHA-256 `86edb104be7febf657345de21c238555bc5367d975b916dfe0552aff9beaea57`; 3/3 tests, Lintian PASS-errors, 105 ABI exports, APT closure, consumer smoke and Python import all PASS.

Shared rootfs artifact `10615785991` has artifact SHA-256 `a90862d653fcb886a11f37116869dd32f7fee425982cc9995271db60c70a45df`; rootfs content SHA-256 is `0438cb6edfece79dcb08b47bdb6a15565919d8e41d831a26e1ca094d1f329576`.

Batch 2 is now **5/5 PASS** and all five selected nodes are downstream-eligible. This closure does not publish to APT and does not authorize any stable promotion.
