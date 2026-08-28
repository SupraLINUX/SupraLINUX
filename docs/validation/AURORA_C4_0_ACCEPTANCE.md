# Aurora C4.0 Acceptance Record

Status: **ACCEPTED / GREEN**

This record permanently captures the evidence used to accept the Aurora C4.0 surface-and-contract inventory gate. C4.0 certifies coverage, ownership and traceability of the currently shipped Plasma surface; it does **not** certify the end-to-end behavior of the later feature gates.

## Accepted source state

- Repository: `SupraLINUX/SupraLINUX`
- Branch under test: `development`
- Technical source commit: `091024257ba346e2c3dac1b462ab2b207111a515`
- Commit message: `test: cover complete Plasma desktop recommends set`
- C4.0 workflow: `.github/workflows/c4-0-surface-validation.yml`
- Workflow run: `33139069857`
- Run number: `7`
- Run attempt: `1`
- Accepted job: `98745608607` (`Inventory and reconcile the Aurora Plasma surface`)
- Workflow/job conclusion: `success`

C1, C2 and C3 remained closed. The accepted C4.0 source change set did not alter Aurora product packages after the previously certified session baseline; C4.0 exercised the package-defined system only to establish the complete certification surface.

## Persistent runtime evidence

GitHub Actions artifact:

- Name: `aurora-c4-0-surface-diagnostics-33139069857-1`
- Artifact ID: `9673344706`
- Artifact size reported by GitHub: `191005` bytes
- Artifact digest reported by GitHub: `sha256:f843fc2d82226e49faa6534de4bb0c0d2a1d0f7d334b4a5524db568459e97f76`
- Artifact created: `2026-08-28T03:38:48Z`

The downloaded ZIP independently hashed to the exact same SHA-256 value.

The artifact contained **68 files**, totaling **1,157,203 bytes** after extraction. Every file was read with strict UTF-8 decoding before acceptance. No file contained NUL bytes or Unicode replacement characters.

Representative evidence hashes:

| File | Bytes | Lines | SHA-256 |
| --- | ---: | ---: | --- |
| `aurora-c4-0-serial.log` | 84,096 | 1,069 | `bcf0dbaa1cc691fff6a826bef4f14d4917c78e969d771b12aefcf67dc84b1177` |
| `aurora-c4-0-wayland-session.log` | 297 | 5 | `6110a2028088853d49af92da96d75aad7bd20fd65aac8bc1d05a7d2fbf5c22e7` |
| `c4-0-validation.log` | 754,110 | 10,288 | `617c87f27fd31bd6b2e84c461d647d6132d2b67107f1f5338de97db056eb3b30` |
| `c4-0-extended-inventory.log` | 442 | 8 | `30f894daea5a035618a79d22d0ccee2dfd7c0e6da10da304398346e165b3648e` |
| `c4-0-reconcile.log` | 505 | 12 | `04bc74921720f949844a6c96d717c2b57e323fc86cb9fe12949aed78c58a6352` |
| `debootstrap.log` | 15,037 | 442 | `6c1eef7ef6fb226f4f07b02bb4de8c85af27a3400801aa846f657f8f6b421145` |
| `rootfs-discover-simulation.log` | 278 | 7 | `25be157344b48fdd0d93e635c15c42aed7ffcb073d43f82360306692c56558e5` |

The artifact ZIP digest above is the durable integrity anchor for the complete 68-file evidence set.

## Deterministic guest evidence

The serial console contains exactly one authoritative guest sequence:

- `AURORA_C4_0_CHECK_START`
- `AURORA_C4_0_STAGE=SESSION`
- `AURORA_C4_0_STAGE=KCMS`
- `AURORA_C4_0_STAGE=DEPENDENCIES`
- `AURORA_C4_0_STAGE=PORTALS`
- `AURORA_C4_0_STAGE=AUXILIARY`
- `AURORA_C4_0_STAGE=COVERAGE`
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-001`
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-002`
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-003`
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-004`
- `AURORA_C4_0_CAPABILITY_PASS=AUR-COVER-005`
- `AURORA_C4_0_STAGE=STABILITY`
- `AURORA_C4_0_STAGE=COMPLETE`
- `AURORA_C4_0_SUCCESS`

There is no `AURORA_C4_0_FAILURE` marker in the accepted serial evidence.

The host-side extended inventory and reconciliation add the remaining coverage assertion:

- `AURORA_C4_0_EXTENDED_INVENTORY_SUCCESS`
- `AURORA_C4_0_RECONCILE_MATCH=kwin-surfaces`
- `AURORA_C4_0_RECONCILE_MATCH=integration-surfaces`
- `AURORA_C4_0_RECONCILE_MATCH=plasma-recommends`
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-002`
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-003`
- `AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-006`
- `AURORA_C4_0_RECONCILE_SUCCESS`

## Coverage reconciliation proven

The accepted artifact proves exact equality between runtime discovery and the version-controlled C4.0 contracts for all six required coverage classes:

| Coverage class | Runtime entries | Result |
| --- | ---: | --- |
| Plasma KCM IDs | 100 | actual = expected |
| Direct `supralinux-desktop` dependencies | 61 | actual = expected |
| Installed portal descriptors | 3 | actual = expected |
| KWin surfaces | 29 | actual = expected |
| Plasma/KDED/KIO integration surfaces | 119 | actual = expected |
| `plasma-desktop` feature `Recommends` | 36 | actual = expected |

For every class above, both `unknown-*` and `missing-*` result files are empty.

The following ownership result files are also empty, proving that no discovered in-scope surface lacked a package owner:

- `unresolved-kcm-owners.txt`
- `unresolved-portal-owners.txt`
- `unresolved-kwin-surface-owners.txt`
- `unresolved-plasma-applet-plugin-owners.txt`
- `unresolved-plasma-surface-owners.txt`
- `unresolved-kded-plugin-owners.txt`
- `unresolved-kio-surface-owners.txt`

`manifest-capability-ids-missing-from-matrix.txt` is empty, proving that every capability ID referenced by the C4.0 manifests exists in the canonical integration matrix.

## Portal/session evidence

The live Plasma environment reports `XDG_CURRENT_DESKTOP=KDE`.

The installed portal routing evidence is:

```ini
[preferred]
default=kde
org.freedesktop.impl.portal.Settings=kde;gtk;
org.freedesktop.impl.portal.Secret=kwallet
```

C4.0 accepts this only as inventory/routing evidence. Functional FileChooser, Flatpak permission, Secret/KWallet, screenshot and screen-sharing behavior remains owned by C4.6 and C4.7.

## Full-log warning classification

The full accepted logs were reviewed for failures, errors, warnings, crashes, panic/OOM indicators, emergency/rescue state, missing files and timeout indicators.

### Rootfs composition messages

The large `c4-0-validation.log` contains the same expected chroot-composition class already understood from earlier certified gates:

- `invoke-rc.d` cannot determine a runlevel and `policy-rc.d` intentionally denies service starts/reloads while composing the rootfs;
- NetworkManager cannot create an `NMClient` or reload connections because the composition chroot has no running system bus;
- one PackageKit/system-bus operation cannot connect for the same reason;
- one command reports that systemd is not PID 1 inside the chroot;
- Plymouth's compatibility `update-rc.d` warnings;
- Chrony's `dpkg-statoverride` warning before its runtime log directory exists;
- rescue/emergency symlink creation by `grub-initrd-fallback`, not activation of those targets.

The composition completes, the real guest boots and the authoritative C4.0 runtime markers pass.

### First-login Plasma session diagnostics

`aurora-c4-0-wayland-session.log` contains the same five asynchronous first-login startup diagnostics already classified under C3:

- an early read of `~/.config/kdedefaults/package` before the file exists;
- `/usr/bin/xrdb: Can't open display ''`;
- `xcb_connect() failed`;
- two `QPixmap: QGuiApplication must be created before calling defaultDepth()` lines.

C4.0 subsequently obtains the live Plasma session environment, Wayland/X11 session plumbing and complete inventory, reaches `STABILITY`, and emits success. These messages therefore do not represent a C4.0 coverage failure.

### VM/kernel and shutdown observations

The virtual CPU reports the same speculative-execution warning class seen in earlier VM gates. It is a host/virtual-CPU exposure, not a missing Aurora desktop component.

After `AURORA_C4_0_SUCCESS`, the deliberate shutdown transaction logs an `rfkill` device job that cannot be enqueued because shutdown is already in progress. It occurs after the accepted success marker and does not affect the running-state evidence.

No C4.0 runtime crash, OOM, emergency/rescue activation, unresolved surface owner, unknown surface, missing expected surface or reconciliation failure was found.

## Scope of acceptance

C4.0 proves that, for the accepted Ubuntu 26.04 / Plasma package-defined Aurora composition:

- the currently exposed KCM surface is completely enumerated against the versioned contract;
- the current KWin plugin/configuration surface is completely mapped;
- the current Plasma applet/plasmoid, KDED and KIO integration surface is completely mapped;
- every current direct `supralinux-desktop` dependency has a capability/policy owner;
- installed portal descriptors and routing are inventoried;
- every current `plasma-desktop` feature recommendation is explicitly owned by the Aurora certification model;
- discovered surfaces have resolvable package ownership;
- every manifest capability ID resolves to the canonical matrix;
- the live Plasma Wayland session remains stable through the inventory probe.

C4.0 does **not** prove that the mapped features work end-to-end. Those claims remain pending in C4.1 through C4.15 and must not be marked passed from C4.0 evidence alone.

## Regression rule

C4.0 is now closed and must not be reopened casually. Re-run C4.0 when a later change can alter the shipped or discovered surface, including relevant Plasma/KWin/KIO/KDED/portal package changes, `supralinux-desktop` dependency changes, or Ubuntu SRUs that change the effective installed feature graph.

Documentation-only acceptance/status changes do not invalidate this record.

## Verdict

Aurora C4.0 is formally accepted as **GREEN** for the defined surface-and-contract coverage scope.

C4.1 is now unblocked. Product package/dependency changes remain evidence-driven and must follow the C4 regression rules.