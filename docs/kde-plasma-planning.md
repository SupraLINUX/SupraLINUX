# KDE Plasma 6.7.5 planning

## Canonical upstream selection

As of 2026-10-01, SupraLINUX selects KDE Plasma **6.7.5** as the latest official stable Plasma release compatible with the Ubuntu 26.04 application contract.

Upstream references:

- Plasma 6.7.5 source release: https://kde.org/info/plasma-6.7.5/
- Plasma release schedule and dependency policy: https://community.kde.org/Schedules/Plasma_6

Plasma 6.8 is still beta in this lifecycle and is therefore not canonical. Plasma 6.7 requires Qt 6.10 and KDE Frameworks 6.26; SupraLINUX currently provides Ubuntu Qt 6.10.2 and KDE Frameworks 6.30.0, so the selected stable release does not require a new Qt/platform substitution.

The Plasma 6.7.5 release page publishes 75 source tarballs and SHA-256 digests. All 75 are represented in `manifests/kde-plasma.json`. No upstream source component is silently excluded at inventory time.

## Planning boundary

This phase is **planning only**:

- runner: GitHub-hosted Ubuntu 26.04, non-authoritative preflight;
- no `sbuild` package execution;
- no package Attempt is consumed;
- no canonical package state changes;
- stable publication remains unauthorized.

The first workflow downloads every official Plasma 6.7.5 tarball, verifies its release-page SHA-256, scans upstream CMake metadata, and emits candidate internal/external dependency evidence. Those candidate edges are not the canonical DAG until they are reviewed and promoted.

## DAG policy

KWin is a normal node in the Plasma release DAG, not a separately versioned desktop authority. It receives additional release-relevant compositor/session gates later because KWin and the Plasma session cross the graphics/session boundary.

The intended lifecycle is:

```text
upstream Plasma 6.7.5 inventory
        ↓
source SHA / dependency discovery
        ↓
provider audit (Ubuntu / Frameworks / Plasma internal / external)
        ↓
package-contract + source materialization
        ↓
topological Plasma DAG
        ↓
parallel independent package nodes
        ↓
authoritative KVM package proof
        ↓
KWin / plasma-workspace / session integration proof
```

Mobile, Bigscreen and other profile boundaries are deliberately not decided by the inventory step. The complete upstream release is first discovered; profile/build boundaries must be justified from upstream dependency and packaging evidence rather than guessed in advance.
