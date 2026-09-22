# KDE Frameworks Tier 3 package-contract review

Status: **pending CI**

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
