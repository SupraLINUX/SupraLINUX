# KDE Tier 1 global discovery strategy

Date: **2026-09-16**

Status: **ADOPTED**

## Decision

SupraLINUX will no longer require one package batch to become fully green before discovering failures in unrelated, independently runnable KDE nodes.

The canonical build strategy is a DAG-wide discovery campaign:

1. evaluate the current DAG and retained PASS artifacts;
2. attempt every node that is topologically runnable **and** has a runner capable of validating its real package surface;
3. parallelize independent nodes and use `fail-fast: false`;
4. continue after independent `FAIL` results;
5. never attempt a dependent node using artifacts from a failed predecessor;
6. classify an unattempted dependent as `BLOCKED`, never `FAIL`;
7. keep every attempted node's logs, sources, hashes, `.deb`, `.changes`, `.buildinfo`, manifests and CI evidence separately;
8. aggregate failures by root cause;
9. after a fix, rerun the affected nodes for fast feedback;
10. after a remediation set, repeat the complete runnable campaign to detect regressions and newly exposed failures.

## Important distinction: DAG result vs campaign readiness

`PASS`, `FAIL` and `BLOCKED` describe build/DAG results.

Before a node is attempted, the discovery planner may additionally classify it as:

- `runnable`: the current runner can produce a meaningful real attempt;
- `lane-pending`: the dependency DAG permits the attempt, but the correct runner lane is not implemented yet;
- `dependency-blocked`: a required local predecessor has no retained `PASS` artifact.

`lane-pending` is **not** `FAIL` and is **not** `BLOCKED`. Calling it either would manufacture a false package result from missing CI capability.

## Why this changes the previous operating pattern

Batch 7 demonstrated the value of broad failure discovery inside one independent set. Its first attempts exposed common causes across KCalendarCore, KCoreAddons and KWidgetsAddons (Clang/LLVM, then the Setuptools backend), allowing one root-cause correction to advance three packages at once.

The same principle now applies across the full Tier 1 frontier. A still-failing KCalendarCore must not prevent an unrelated KConfig, KI18n, Sonnet, Kirigami, KQuickCharts, KUserFeedback or Prison attempt once the appropriate runner lane exists.

## Current factual snapshot

The canonical Tier 1 manifest currently contains **18 promoted PASS** nodes and **11 unpromoted nodes**.

Current runnable lane:

- KCalendarCore
- KCoreAddons
- KWidgetsAddons

Runner implementation still required before meaningful attempts:

- multi-ABI: KConfig, KI18n, Sonnet;
- QML/multisurface: Kirigami, KQuickCharts;
- multi-surface/optional-provider: KUserFeedback, Prison.

KGuiAddons remains dependency-blocked until a retained local KCoreAddons PASS can feed its development surface.

## Authority and provider

This strategy does not change desktop authority. KDE upstream stable still defines KDE sources, features, defaults and dependencies. Ubuntu Resolute may provide dependencies when they satisfy those requirements. Runner lanes exist to validate the real KDE-selected surfaces; they must not make a package pass by disabling upstream functionality merely because a downstream distribution did so.

## Evidence model

There is no single monolithic build log. A campaign has one summary plus per-node evidence. This keeps failures independently diagnosable and prevents one large log from hiding package boundaries.

A campaign summary may group root causes, but the original node artifacts remain immutable historical evidence.
