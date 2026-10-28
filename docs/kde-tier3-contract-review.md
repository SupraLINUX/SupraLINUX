# KDE Frameworks Tier 3 package-contract review

Status: **PASS — explicit contract decisions required**

Reviewed: **2026-09-22**

## Purpose

The Tier 3 technical-reference and packaging-tree captures are complete. This gate compares the exact pinned Ubuntu Resolute and Debian sid packaging trees for all 20 KDE Frameworks 6.30 nodes before SupraLINUX authorizes any package contract or materialization.

KDE upstream remains source, feature and dependency authority. Ubuntu is a compatibility/platform reference and Debian is a packaging reference. A packaging difference is evidence to review, not a reason to make either distribution authoritative.

## Evidence captured

For every node the review records:

- exact Ubuntu/Debian packaging-tree linkage and SHA-256 identity;
- source Build-Depends and Build-Depends-Indep deltas;
- binary Depends, Recommends, Suggests, Provides, Replaces, Breaks and Conflicts deltas;
- changes to `debian/rules`;
- `.install`, `.symbols`, triggers and maintscript deltas;
- the KDE-upstream dependency classes already recorded in the Tier 3 DAG.

The review deliberately does not fail merely because Ubuntu and Debian differ. It fails only if evidence is missing, hashes drift, package identities diverge unexpectedly, or the promoted tree artifact no longer matches the canonical manifest.

## State semantics

`package_state_effect=none`.

All 20 canonical Tier 3 Frameworks remain pending. This gate does not authorize materialization, does not build packages and does not make any node downstream-eligible.

After the evidence PASS is promoted, each delta must be classified into an explicit SupraLINUX package contract. Only then may materialization be authorized.


## Initial CI integration correction

The first review workflow run, `35730349511`, failed before any Framework was reviewed. `actions/download-artifact` correctly downloaded promoted artifact `10694324518`, but placed its contents under a single artifact-name subdirectory while the reviewer expected `index.json` at the requested parent path.

This is an **INFRA/integration failure**, not a Tier 3 contract FAIL and not a package attempt. No package state changed and no contract decision was produced.

The reviewer now discovers exactly one artifact root containing `index.json`, `result.json` and `trees/`, revalidates the promoted hashes there, and emits a diagnostic result artifact even when a pre-review integration error occurs.


## Review evidence PASS

Run `35730670337`, job `106755175676`, artifact `10695332103`, artifact SHA-256 `4fb1b37f392e8ce18ee0b4112fafc496d20deacb375d767c4b463f0ec1a7e8c6`: **PASS**.

Review SHA-256: `687c2d7962515778b04e07b3a6a00b72453f9021d75d8abac96a3f84756ba358`.

The review revalidated the promoted packaging-tree index and all 20 node mappings. Ubuntu and Debian keep identical binary-package identities for **20/20** nodes, but every node has at least one packaging delta requiring an explicit SupraLINUX contract decision.

Observed delta counts: **15** Build-Depends, **20** binary relationships, **13** rules, **20** install manifests, **14** symbols and **0** maintscript deltas.

This PASS is evidence only. Materialization and package builds remain blocked. The next gate is `tier3-package-contract-decision`.
