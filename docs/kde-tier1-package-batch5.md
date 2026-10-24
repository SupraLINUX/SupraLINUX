# KDE Frameworks 6.30 Tier 1 — package Batch 5

Status: **closed — 3/3 PASS**
Last reviewed: **2026-09-15**

## Selection

Batch 5 contains three independent Tier 1 nodes whose only KDE DAG predecessor is the retained ECM PASS and whose ABI surface fits the current single-primary-library runner:

- KIdleTime;
- ModemManagerQt;
- NetworkManagerQt.

The batch is now canonically closed. Tier 1 is **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**.

## KIdleTime PASS

First real package attempt: run `35014875475`, commit `30b5dcd293527b488c88cf0a861883ee869e3ea0`.

- package `6.30.0-0supralinux1`;
- job `104535671033`;
- artifact `10414598079`;
- artifact SHA-256 `272ccad537d21905cf75a1add74e937d176c20c05c38bf967226fef4ab28b605`;
- tests `1/1 PASS`;
- Lintian errors gate: PASS;
- SONAME `libKF6IdleTime.so.6`;
- consumer smoke: PASS;
- retained ECM predecessor `6.30.0-0supralinux3`.

The later Batch 5 remediation delta did not change any KIdleTime build input, so run `35021323444` intentionally scope-skipped it and retained this PASS.

## NetworkManagerQt PASS

First real package attempt: run `35014875475`, commit `30b5dcd293527b488c88cf0a861883ee869e3ea0`.

- package `6.30.0-0supralinux1`;
- job `104535671250`;
- artifact `10414714325`;
- artifact SHA-256 `abf927b5749b34094d2b5ee530831f64638ba116a83e8b82f925a758aa018ad4`;
- tests `38/38 PASS` after excluding only the three documented tests requiring a live NetworkManager service;
- Lintian errors gate: PASS;
- SONAME `libKF6NetworkManagerQt.so.6`;
- consumer smoke: PASS;
- QML package contract retained.

Run `35021323444` intentionally scope-skipped this node because its package-consumed inputs were unchanged.

## ModemManagerQt attempt history

### `6.30.0-0supralinux1` — real FAIL

Run `35014875475`, job `104535671188`, artifact `10415586492`, artifact SHA-256 `f79f98cc73f561e5750c4db7917917a043f260131af0ac19180fd835dee78af7`.

The package built and all `11/11` tests passed, but the sbuild Lintian gate rejected `_ZSt19piecewise_construct@Base` because dpkg-gensymbols assigned the current Debian revision as its minimum version. This is a real node FAIL, not BLOCKED.

### `6.30.0-0supralinux2` — real FAIL

A deterministic, hash-locked symbols transform inserted exactly:

`(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0`

Evidence hashes:

- baseline symbols SHA-256 `70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2`;
- transformed symbols SHA-256 `b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f`;
- transform script SHA-256 `f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b`.

Run `35017509303`, job `104544555425`, artifact `10416692119`, artifact SHA-256 `2b081f989d42f6d4820b238c9e739ccb4104080ceae7a49aa49cb20305eb66d7`, again passed `11/11` tests and proved the symbols transform. Lintian then rejected `debian/rules` because it invokes Python without an explicit Python build prerequisite. This is a second real node FAIL.

### `6.30.0-0supralinux3` — PASS

Revision `-3` retained the reviewed symbols transform and added only `python3:any` to Build-Depends. KDE source, selected Qt and provider requirements were unchanged.

Repository Policy for the remediation head: run `35021323425` — PASS.

Batch 5 run `35021323444` rebuilt only ModemManagerQt:

- job `104557423664`;
- artifact `10417683848`;
- artifact SHA-256 `42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7`;
- tests `11/11 PASS`;
- Lintian errors gate: PASS;
- SONAME `libKF6ModemManagerQt.so.6`;
- consumer smoke: PASS;
- retained ECM predecessor `6.30.0-0supralinux3`.

The two earlier FAIL attempts remain historical evidence. Only the `-3` PASS is downstream-eligible.

## Provider evidence

KDE upstream 6.30.0 remains authority. Ubuntu Resolute is only provider.

KDE requires pkg-config module `ModemManager >= 1.0`; Ubuntu Resolute supplies it through `modemmanager-dev`. Targeted provider evidence:

- run `35012023822`;
- job `104526071758`;
- commit `48fd01bfa7b254b5e5c8447b3d609f76a91f786f`;
- artifact `10414525047`;
- artifact SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`;
- result PASS;
- claim: provider availability only, non-authoritative.

## Canonical closure

The Batch 5 campaign ledger, Tier 1 manifest and global KDE DAG now agree:

**16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**.

KIdleTime, ModemManagerQt and NetworkManagerQt are all canonical PASS and downstream-eligible. Historical FAILs remain attached to ModemManagerQt as attempt history and are not counted as current FAIL.

Hosted package-preflight remains non-authoritative relative to the future KVM/JIT certification. KConfig remains deferred until the runner supports its multi-library ABI contract.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
