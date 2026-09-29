# Tier 1 global discovery status — 2026-09-16

Status: **strategy adopted; lane expansion in progress**

## Promoted state

- Tier 1: **18 PASS / 11 pending / 0 current promoted FAIL / 0 BLOCKED**.
- Historical package FAIL attempts remain retained in their batch ledgers/artifacts.
- PR #1 remains Draft and must not be merged until its independent merge gates are satisfied.

## Discovery frontier

### Runnable now

- `kcalendarcore`
- `kcoreaddons`
- `kwidgetsaddons`

These already have a real clean-package runner. Their current failures remain worth fixing, but they no longer serialize unrelated discovery work.

### Lane implementation pending

Multi-ABI:
- `kconfig`
- `ki18n`
- `sonnet`

QML/multisurface:
- `kirigami`
- `kquickcharts`

Multi-surface/optional-provider:
- `kuserfeedback`
- `prison`

These are **not package FAILs**. They are not attempted until their runners can validate their actual package surfaces.

### Dependency-blocked

- `kguiaddons` requires a retained local `kcoreaddons` PASS for the relevant development/runtime contract.

## Next implementation order

1. Finish/publish the already prepared Batch 7 remediation while leaving unrelated work unblocked.
2. Implement the multi-ABI lane and attempt KConfig, KI18n and Sonnet together with `fail-fast: false`.
3. Implement the QML/multisurface lane and the optional-provider lane.
4. Run every newly runnable node, preserve per-node evidence and aggregate root causes.
5. Make KGuiAddons runnable immediately after KCoreAddons produces a retained PASS.
6. Repeat the full runnable campaign after remediation sets.
