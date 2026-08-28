# Aurora C4.0 Acceptance Record

Status: **ACCEPTED / GREEN / CLOSED**

C4.0 certifies coverage, ownership and traceability of the currently shipped Aurora Plasma surface. It does **not** certify end-to-end feature behavior; those claims belong to C4.1 through C4.15.

## Current accepted source state

- Repository: `SupraLINUX/SupraLINUX`
- Branch: `development`
- Current accepted technical source commit: `57b296054efc391ec986ed57a57a9a028601de76`
- Commit message: `c4: map Baloo runtime integration surfaces`
- Workflow: `.github/workflows/c4-0-surface-validation.yml`
- Workflow run: `33211234383`
- Run number: `14`
- Accepted job: `98984662738` (`Inventory and reconcile the Aurora Plasma surface`)
- Workflow/job conclusion: `success`

This run is an intentional C4.0 regression revalidation. C4.0 had already been accepted and closed; it was reopened only because the evidence-driven addition of `baloo6` to `supralinux-desktop` for `AUR-KCM-003` changed both the direct dependency graph and the shipped KDED/KIO surface.

C1, C2 and C3 remained closed. The Baloo correction does not alter the certified boot/session policy or core Plasma/KWin session packages.

## Current persistent evidence

GitHub Actions artifact:

- Name: `aurora-c4-0-surface-diagnostics-33211234383-1`
- Artifact ID: `9701846713`
- Artifact digest reported by GitHub: `sha256:6f10d1643f72e852d89ab5566d193942ce36957c445d916e73148beb0c26aab1`
- Downloaded ZIP SHA-256: `6f10d1643f72e852d89ab5566d193942ce36957c445d916e73148beb0c26aab1`
- Artifact files: **68**
- Extracted bytes: **1,157,703**
- Strict UTF-8 decode failures: **0**
- Files containing NUL bytes: **0**
- Files containing Unicode replacement characters: **0**

The artifact digest is the integrity anchor for the complete accepted evidence set.

## Why C4.0 was re-run

C4.1b File Search/Baloo preflight run `33205267606` proved a real SupraLINUX dependency omission:

- `kcm_baloofile` was exposed and owned by `plasma-desktop`;
- File Search configuration was enabled;
- `libkf6baloo6` was present;
- `baloo6` was absent;
- `balooctl6`, `baloosearch6`, `baloo_file`, `kde-baloo.service` and `org.kde.baloo` were unavailable;
- attempting to start `kde-baloo.service` returned `Unit kde-baloo.service not found`.

The product fix added only `baloo6` as an explicit `supralinux-desktop` dependency. C4.0 then correctly detected the resulting contract delta before it was accepted:

- direct dependency: `baloo6`;
- KDED plugin: `baloosearchmodule`;
- KIO worker: `baloosearch`;
- KIO worker: `tags`;
- KIO worker: `timeline`.

Ownership inventory resolved all five to `baloo6 6.24.0-0ubuntu1`. The versioned manifests map them to `AUR-KCM-003 / C4.1`.

## Current coverage reconciliation

The post-Baloo accepted artifact proves exact equality between runtime discovery and the version-controlled C4.0 contracts:

| Coverage class | Runtime entries | Result |
| --- | ---: | --- |
| Plasma KCM IDs | 100 | actual = expected |
| Direct `supralinux-desktop` dependencies | 62 | actual = expected |
| Installed portal descriptors | 3 | actual = expected |
| KWin surfaces | 29 | actual = expected |
| Plasma/KDED/KIO integration surfaces | 123 | actual = expected |
| `plasma-desktop` feature `Recommends` | 36 | actual = expected |

All current `unknown-*` and `missing-*` result files are empty.

All ownership result files are empty:

- `unresolved-kcm-owners.txt`;
- `unresolved-portal-owners.txt`;
- `unresolved-kwin-surface-owners.txt`;
- `unresolved-plasma-applet-plugin-owners.txt`;
- `unresolved-plasma-surface-owners.txt`;
- `unresolved-kded-plugin-owners.txt`;
- `unresolved-kio-surface-owners.txt`.

`manifest-capability-ids-missing-from-matrix.txt` is also empty.

The host-side evidence contains:

- `AURORA_C4_0_EXTENDED_INVENTORY_SUCCESS`;
- `AURORA_C4_0_RECONCILE_MATCH=kwin-surfaces`;
- `AURORA_C4_0_RECONCILE_MATCH=integration-surfaces`;
- `AURORA_C4_0_RECONCILE_MATCH=plasma-recommends`;
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-002`;
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-003`;
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-006`;
- `AURORA_C4_0_RECONCILE_SUCCESS`.

## Deterministic guest evidence

The accepted serial evidence contains the complete guest path:

- `AURORA_C4_0_CHECK_START`;
- `AURORA_C4_0_STAGE=SESSION`;
- `AURORA_C4_0_STAGE=KCMS`;
- `AURORA_C4_0_STAGE=DEPENDENCIES`;
- `AURORA_C4_0_STAGE=PORTALS`;
- `AURORA_C4_0_STAGE=AUXILIARY`;
- `AURORA_C4_0_STAGE=COVERAGE`;
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-001` through `AUR-COVER-005`;
- `AURORA_C4_0_STAGE=STABILITY`;
- `AURORA_C4_0_STAGE=COMPLETE`;
- `AURORA_C4_0_SUCCESS`.

There is no `AURORA_C4_0_FAILURE` marker.

At `STABILITY`, the harness verifies that the original KWin Wayland and plasmashell PIDs remain alive and unchanged. The accepted run passed these assertions. The accepted Wayland session log contains no crash/failure event, and the artifact contains no unexplained runtime coredump, segfault, OOM, emergency/rescue activation, unknown surface, missing expected surface or unresolved owner.

## Baloo-specific C4.0 evidence

The accepted inventory records:

- `baloo6 6.24.0-0ubuntu1` installed as a direct dependency owned by `AUR-KCM-003 / C4.1`;
- `KDED_PLUGIN baloosearchmodule` owned by `baloo6`;
- `KIO_WORKER baloosearch` owned by `baloo6`;
- `KIO_WORKER tags` owned by `baloo6`;
- `KIO_WORKER timeline` owned by `baloo6`;
- `plasma-baloorunner.service` present in the relevant user-unit inventory;
- activatable user-bus name `org.kde.runners.baloo` present.

These facts prove that the newly shipped Baloo surfaces are fully accounted for. They do **not** prove that indexing or searching works. `AUR-KCM-003` therefore remains `PENDING-C4` until its dedicated behavioral contract passes.

## Portal/session scope

The live Plasma environment identifies KDE and the existing portal routing remains inventoried. C4.0 accepts portal descriptors/routing only as surface evidence. Functional FileChooser, Flatpak permissions, Secret/KWallet, screenshot and screen-sharing behavior remains owned by C4.6/C4.7.

## Historical initial acceptance

The original C4.0 acceptance remains valid historical evidence for the pre-Baloo composition:

- source commit: `091024257ba346e2c3dac1b462ab2b207111a515`;
- run: `33139069857` (#7);
- job: `98745608607`;
- artifact: `aurora-c4-0-surface-diagnostics-33139069857-1`;
- artifact ID: `9673344706`;
- artifact digest: `sha256:f843fc2d82226e49faa6534de4bb0c0d2a1d0f7d334b4a5524db568459e97f76`;
- inventory: 100 KCMs, 61 direct dependencies, 3 portals, 29 KWin surfaces, 119 integration surfaces and 36 Plasma feature `Recommends`;
- result: zero unknown/missing/unresolved owners and stable live Plasma Wayland session.

The post-Baloo run `33211234383` supersedes those inventory counts as the current accepted Aurora composition while preserving the original run as provenance.

## Regression rule

C4.0 is closed again. Re-run it only when a later change can alter the effective shipped/discovered surface or dependency graph, including relevant Plasma/KWin/KIO/KDED/portal package changes, `supralinux-desktop` dependency changes or Ubuntu SRUs that alter the installed feature graph.

Documentation-only acceptance/status changes do not invalidate C4.0 and do not reopen C1-C3.

## Verdict

Aurora C4.0 is formally **ACCEPTED / GREEN / CLOSED** for HEAD `57b296054efc391ec986ed57a57a9a028601de76` and the post-Baloo composition described above.

C4.1 remains **OPEN / ACTIVE**. `AUR-KCM-003` is not certified by this record; only its surface, ownership and product dependency closure are established here.
