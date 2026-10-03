# ADR — Historical evidence is separate from live lifecycle state

Status: **accepted**  
Date: **2026-09-26**

## Context

KIO diagnostics Round 12–18 were created while Level 1 Attempt 7 was the live canonical state. Several closed diagnostic validators later kept reading the current Tier 3 and Level 1 manifests and therefore asserted that Attempt 7 had to remain current forever.

After Round 18 legitimately materialized KIO `6.30.0-0supralinux8` for Attempt 8, those validators became false-red even though their own workflow, artifact, SHA-256 and diagnostic conclusions had not changed.

## Decision

Closed diagnostic and audit validators are **historical evidence validators**.

They validate only their own immutable/historical contract: identity, authority, recorded snapshot, workflow/job/artifact/SHA-256 evidence, predecessor/handoff data, conclusions, and non-promoting safety invariants.

They must not read mutable live state from current Tier 3, Level 1, package-contract, materialization, build-campaign or DAG manifests.

Current lifecycle state is validated only by the current lifecycle/remediation validator.

Repository Policy enforces this boundary through `scripts/validate_kde_tier3_historical_boundary.py`.

## Consequences

Advancing Attempt 8, a future Attempt 9, or eventually promoting KIO to PASS cannot invalidate a closed diagnostic merely because live state changed.

Historical evidence stays independently checkable. Live state remains strict but has one current owner instead of being reasserted by every old round.

This ADR changes no package result, DAG state or stable-promotion policy.
