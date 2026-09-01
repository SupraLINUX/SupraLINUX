# Aurora build/infrastructure cleanup ledger

Status: **ACTIVE**

Purpose: keep an explicit record of temporary build infrastructure, caches, diagnostic workflows, host paths, and other engineering artifacts that must be removed when their retention condition expires. This file is intentionally long-lived; entries are removed only after cleanup is executed and verified.

## Rules

- Do not delete an item merely because it is currently unused if it is still part of an open certification or required for reproducibility.
- Every host-side path must record the machine, purpose, provenance, retention condition, deletion command/procedure, and verification step before it is created.
- Temporary CI workflows remain until the investigation/certification evidence they support has been incorporated into durable documentation and no rerun is required.
- Cleanup must not remove canonical certification evidence, source provenance, manifests, or release artifacts required to reproduce Aurora.
- Mark an entry `REMOVED` only after verification; do not silently delete the row.

## Ledger

| Item | Location | Status | Purpose | Remove when | Cleanup / verification |
|---|---|---|---|---|---|
| Certified Ubuntu snapshot slice | `espadarunica:/srv/supralinux/archive/20260829T022000Z/` | **PLANNED — NOT CREATED** | Local immutable copy of the Ubuntu archive objects required by Aurora KSQ, pinned to snapshot `20260829T022000Z`, to avoid repeated remote Snapshot Service downloads while preserving exact provenance. | Only after Aurora no longer requires this snapshot for reproducible build/regression/rollback, or after it has been migrated to another documented durable store and verified byte-for-byte. | Procedure will be recorded before creation. Before deletion, verify replacement/retention requirements and retained manifests/hashes. After deletion, verify path absent and no workflow/config references it. |
| GitHub-hosted parity diagnostic | `.github/workflows/ksq-github-hosted-parity.yml` | **RETAIN TEMPORARILY** | Measured actual GitHub-hosted container/userns behavior for comparison with the self-hosted KSQ runner. | After KSQ-1 runner architecture is certified and the relevant evidence/results are fully recorded in durable validation docs. | Delete workflow; verify no active validation document depends on rerunning it and no references require the file to exist. |
| sbuild live-transport diagnostic | `.github/workflows/ksq-sbuild-live-transport-probe.yml` | **RETAIN TEMPORARILY** | Isolates `sbuild --chroot-mode=unshare` / AppArmor behavior from Ubuntu Snapshot Service transport failures. Not certification evidence by itself. | After the canonical snapshot-backed sbuild smoke passes and the root-cause evidence has been documented. | Delete workflow; verify canonical smoke remains the sole qualification path and docs preserve diagnostic result. |
| GitHub-hosted snapshot transport probe | `.github/workflows/ksq-snapshot-transport-hosted-probe.yml` | **RETAIN TEMPORARILY** | A/B comparison of Snapshot Service transport on GitHub-hosted vs `espadarunica`. | After snapshot transport/local-slice design is settled and measurements are recorded in durable docs. | Delete workflow; verify measurements/provenance are retained in documentation. |
| KSQ-1 self-hosted representative smoke | `.github/workflows/ksq-1-self-hosted-representative.yml` | **RETAIN — OPEN CERTIFICATION** | Canonical representative smoke used to qualify the self-hosted `mmdebstrap`/`sbuild --unshare` path before source 001. | Do **not** remove while KSQ-1 is open. Reassess only after a replacement canonical path is certified or KSQ-1 closes. | If eventually retired, first identify replacement evidence and run regression; then delete and verify no status/acceptance document references it as executable certification path. |
| Snapshot-slice size measurement workflow | `.github/workflows/ksq-snapshot-slice-size-probe.yml` | **PLANNED — NOT CREATED** | Metadata-only calculation of the local certified snapshot slice; must not download package payloads. | After final slice manifest/size report is committed and independently verified. | Delete workflow and verify the durable size/manifest report remains. |

## Future entries

Add every non-product host modification or disposable engineering resource here before or at the time it is introduced, including local mirrors/caches, temporary AppArmor profiles if superseded, runner-specific test files, transient repositories, diagnostic workflow files, staging directories, and one-off services.
