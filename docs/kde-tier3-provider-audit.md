# KDE Frameworks Tier 3 provider audit

Status: **PASS**

Reviewed: **2026-09-22**

## Authority and scope

This audit covers all **20 canonical Tier 3 Frameworks** selected from KDE Frameworks 6.30.0.

KDE Frameworks 6.30.0 is the current stable upstream release selected by SupraLINUX. KDE defines the required Framework version and requires Qt 6.9.0 or newer. Ubuntu Resolute is evaluated only as a possible provider.

This provider audit is **not a package PASS**. It has `package_state_effect=none`, does not authorize package contracts, does not build any Tier 3 package, and does not insert any Tier 3 node into the canonical PASS DAG.

## Provider rule

For each Tier 3 node, the hosted Ubuntu 26.04 runner reads the source-package candidate from the real Resolute source indexes:

`kf6-<framework>`

The exact candidate is normalized to its upstream version and compared with KDE's selected `6.30.0`.

- exact `6.30.0` match → `ubuntu-compatible`;
- older/newer candidate or no source candidate → `supralinux-required`.

A missing Ubuntu source package is a valid provider decision, not an audit failure. The audit first proves that source indexes themselves are functional using a known KF6 source package, so repository/index failures are not misclassified as provider absence.

## Platform probe

The audit separately installs Ubuntu's `qt6-base-dev` and configures a CMake consumer requiring Qt 6.9 Core. This proves the general platform provider independently from KDE package ownership.

## Precondition

The non-tiered support sub-DAG is already closed:

**Breeze Icons PASS + KDocTools PASS + KDED PASS**.

The 20 canonical Tier 3 Frameworks themselves remain **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** until later package-build gates.

Stable publication remains subject to explicit user approval.


## PASS evidence

Run `35725458767`, job `106737928285`, artifact `10692912109`, artifact SHA-256 `c76ca765d3d4f565ba807a96bc2e6f324cce3dc5f92893c9c5f2c10de8ac07ac`: **PASS**.

Result SHA-256: `8b4b9ab701a4871d0e42831ed7f680acac74419f0ae5314e9ac1129fee608dd1`.

All **20/20** Tier 3 Frameworks require SupraLINUX as provider. Resolute exposes KDE Frameworks upstream 6.24.0 for every audited source package; KIconThemes is packaged as `6.24.0-0ubuntu2`, while the other audited sources are `6.24.0-0ubuntu1`. KDE requires 6.30.0.

Ubuntu remains the selected Qt provider: the runner proved Qt `6.10.2`, satisfying KDE's minimum `6.9.0`.

At the time this audit closed, it changed no package state: Tier 3 remained **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** and every node advanced to `package-contract-required`; package builds remained unauthorized.

The provider-audit evidence is lifecycle-independent: later canonical package states `PASS`, `FAIL`, `BLOCKED`, or `pending` do not invalidate the already-proven provider decision. Package-build results affect downstream eligibility, not provider authority.
