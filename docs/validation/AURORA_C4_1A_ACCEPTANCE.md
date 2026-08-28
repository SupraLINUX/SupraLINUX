# Aurora C4.1a Acceptance Record

Status: **ACCEPTED / GREEN**

This record permanently captures the evidence used to accept the first incremental Aurora C4.1 functional slice. C4.1a certifies exactly two software capabilities:

- `AUR-KCM-002` — Activities create/switch/remove and persistence;
- `AUR-KWIN-004` — Virtual desktop add/switch/remove and persistence.

This acceptance does **not** close C4.1. Every other C4.1 capability remains pending until separately evidenced and accepted.

## Accepted source state

- Repository: `SupraLINUX/SupraLINUX`
- Branch under test: `development`
- Technical source commit: `900205c3bc1c787ca0516972eecbf39ac0bdef9e`
- Commit message: `ci: normalize serial line endings for C4.1a markers`
- Workflow: `.github/workflows/c4-1a-core-validation.yml`
- Workflow run: `33194245130`
- Run number: `5`
- Run attempt: `1`
- Accepted job: `98927202366` (`Certify Activities and virtual desktop behavior`)
- Workflow/job conclusion: `success`

C1, C2, C3 and C4.0 remain closed. No SupraLINUX product package, dependency or product configuration change was required to achieve this acceptance. The implementation changes leading to the accepted run were C4.1a harness corrections only.

## Persistent evidence

GitHub Actions artifact:

- Name: `aurora-c4-1a-core-diagnostics-33194245130-1`
- Artifact ID: `9695328977`
- Artifact size reported by GitHub: `260111` bytes
- Artifact digest reported by GitHub: `sha256:3926d0bcb3a23469cc9e8399404dffad09e61ad6ce95162b19115da73577565d`

The downloaded ZIP independently hashed to exactly the same SHA-256 value.

After extraction, the artifact contained **110 files** totaling **1,437,527 file bytes**. Every file was read with strict UTF-8 decoding before acceptance. There were zero UTF-8 decoding errors, zero NUL-containing files and zero Unicode replacement characters.

Representative evidence hashes:

| File | Bytes | Lines | SHA-256 |
| --- | ---: | ---: | --- |
| `aurora-c4-1a-serial.log` | 164,716 | 3,273 | `d8078aa282f3892bef05e209ba56a8be105a0e01490bcc230fbf9debce0d28b9` |
| `c4-1a-validation.log` | 164,904 | 3,277 | `9c0700f9e85c13b9d377eb63be272c17f9b699ed62a02191d7de5758b310ddd8` |
| `c4-1a-evidence/activities-baseline.txt` | 37 | 1 | `29eef064783e1aa81a14896f119942e4ce38034252a57c8aeadb152dc56af414` |
| `c4-1a-evidence/activities-mutated.txt` | 74 | 2 | `e5226f65eea5593fb0379970babe7ee267cbdd61a8ffea49302e9f26bb4c1472` |
| `c4-1a-evidence/activities-after-reboot.txt` | 74 | 2 | `e5226f65eea5593fb0379970babe7ee267cbdd61a8ffea49302e9f26bb4c1472` |
| `c4-1a-evidence/activities-final.txt` | 37 | 1 | `29eef064783e1aa81a14896f119942e4ce38034252a57c8aeadb152dc56af414` |
| `c4-1a-evidence/virtual-desktops-baseline.txt` | 62 | 1 | `a2dcdf75242831d900b297ca5a3362d834442324c4873e620d446ca163e4ca79` |
| `c4-1a-evidence/virtual-desktops-mutated.txt` | 131 | 1 | `6bbde1146b6d2a4497d9a4db6db66cdac360158acc2452d65eaff7a92735b043` |
| `c4-1a-evidence/virtual-desktops-after-reboot.txt` | 131 | 1 | `6bbde1146b6d2a4497d9a4db6db66cdac360158acc2452d65eaff7a92735b043` |
| `c4-1a-evidence/virtual-desktops-final.txt` | 62 | 1 | `a2dcdf75242831d900b297ca5a3362d834442324c4873e620d446ca163e4ca79` |
| `c4-1a-evidence/package-versions.tsv` | 176 | 5 | `2a7da01af90b7d7aaa32533ac40edc9a67badbf672e2f52443768ed75f097bcd` |
| `c4-1a-evidence/system-failed-units.txt` | 57 | 3 | `4f9e217bc52819ecaff1306b985779c61948779077ed2f6771332c309cd25360` |
| `c4-1a-evidence/user-failed-units.txt` | 57 | 3 | `4f9e217bc52819ecaff1306b985779c61948779077ed2f6771332c309cd25360` |

The artifact ZIP digest above is the durable integrity anchor for the complete 110-file evidence set.

## Deterministic execution sequence

The accepted serial evidence contains the complete two-boot sequence:

- `AURORA_C4_1A_START`
- `AURORA_C4_1A_STAGE=SESSION`
- `AURORA_C4_1A_STAGE=BASELINE`
- `AURORA_C4_1A_STAGE=ACTIVITIES`
- `AURORA_C4_1A_STAGE=VIRTUAL_DESKTOPS`
- `AURORA_C4_1A_STAGE=PERSISTENCE_WRITE`
- `AURORA_C4_1A_STAGE=PHASE1_COMPLETE`
- `AURORA_C4_1A_PHASE1_SUCCESS`
- `AURORA_C4_1A_RESUME`
- `AURORA_C4_1A_STAGE=SESSION_RELOAD`
- `AURORA_C4_1A_STAGE=PERSISTENCE_READ`
- `AURORA_C4_1A_STAGE=CLEANUP`
- `AURORA_C4_1A_STAGE=STABILITY`
- `AURORA_C4_1A_CAPABILITY_PASS=AUR-KCM-002`
- `AURORA_C4_1A_CAPABILITY_PASS=AUR-KWIN-004`
- `AURORA_C4_1A_STAGE=COMPLETE`
- `AURORA_C4_1A_SUCCESS`

There is no `AURORA_C4_1A_FAILURE` marker in the accepted evidence.

The host harness preserves the raw serial log and normalizes only a trailing carriage return while comparing deterministic markers, because QEMU's serial TTY emits CRLF line endings. Marker matching is exact after that transport normalization.

## `AUR-KCM-002` — Activities

Baseline Activity ID:

`bd658de5-c27b-4514-9fa4-bfdcdf68f2a8`

The test created a new Activity through the live `org.kde.ActivityManager` API:

`7216b13a-5c6b-4d64-8608-4ae9dea8b392`

The runtime list changed from one Activity to two, and the new Activity was named `Aurora-C4.1A-Test-Activity`.

The new Activity became current. The negative-path request to switch to the nonexistent UUID `00000000-0000-0000-0000-000000000000` returned semantic result `false`; the valid test Activity remained current.

Before boot 1 was allowed to shut down, the harness required the exact Activity name and current Activity ID to be observable in persistent KConfig state. This avoids racing kactivitymanagerd's delayed configuration sync.

On boot 2:

- the same test Activity ID was present;
- its name was unchanged;
- the same ID was still the current Activity;
- the persisted files matched runtime state;
- the newly started ActivityManager could switch away from the test Activity and back to it.

Cleanup switched back to the original Activity, removed the test Activity and waited until it disappeared from both runtime and persistent KConfig state.

`activities-baseline.txt` and `activities-final.txt` are byte-identical.

Verdict: `AUR-KCM-002` = **PASS-C4**.

## `AUR-KWIN-004` — Virtual Desktops

Baseline virtual desktop state:

- count: `1`;
- desktop ID: `28c5afad-2f4e-48bc-af24-0ac1e4802436`;
- name: `Desktop 1`.

The test created a second desktop through KWin's live `org.kde.KWin.VirtualDesktopManager` API:

- ID: `5b3dd4a9-a033-4795-b0a3-27a2111eec79`;
- name: `Aurora-C4.1A-Test-Desktop`;
- count after mutation: `2`.

The new desktop became current. A negative-path attempt to set the current desktop to the nonexistent UUID did not alter the authoritative current desktop.

Before boot 1 shut down, the harness required the same desktop UUID, name and count to be present in KWin's persistent `[Desktops]` configuration.

On boot 2:

- count remained `2`;
- the same test desktop UUID and name were present;
- the test desktop remained current;
- runtime state matched persistent KWin configuration;
- the newly started KWin could select the persisted test desktop again.

Cleanup restored the original desktop, removed the test desktop, waited for count `1`, verified that the test UUID disappeared from the virtual-desktop API and from the persistent `[Desktops]` state, and returned the current desktop to the original UUID.

`virtual-desktops-baseline.txt` and `virtual-desktops-final.txt` are byte-identical.

KWin may retain auxiliary `[Tiling]` state associated with a previously used desktop UUID in `kwinrc`. C4.1a does not claim byte-for-byte restoration of every unrelated KWin configuration section. The authoritative VirtualDesktopManager topology and its persistent `[Desktops]` state are restored exactly. The auxiliary tiling behavior remains visible to later KWin-focused C4.1 coverage rather than being hidden by this acceptance.

Verdict: `AUR-KWIN-004` = **PASS-C4**.

## Runtime stability

After persistence re-read, API re-exercise and cleanup, the harness held the second-boot session for an additional stability interval and verified that both the same `kwin_wayland` process and the same `plasmashell` process remained alive.

Both failed-unit inventories contain:

```text
0 loaded units listed.
```

No C4.1a runtime coredump, segmentation fault, crash marker, OOM, emergency/rescue transition or C4.1a failure marker was found in the complete accepted artifact.

Package versions recorded by the accepted run:

| Package | Version |
| --- | --- |
| `kactivitymanagerd` | `6.6.6-0ubuntu0.1` |
| `kwin-wayland` | `4:6.6.6-0ubuntu0.1` |
| `plasma-desktop` | `4:6.6.6-0ubuntu0.1` |
| `plasma-workspace` | `4:6.6.6-0ubuntu0.1` |
| `qdbus-qt6` | `6.10.2-1` |

## Full-log classification

All 110 files were reviewed, including the full serial and user journal, rather than accepting the GitHub workflow conclusion alone.

The accepted logs contain several messages outside the two-capability claim. They are classified rather than suppressed:

- QEMU/virtio graphics falls back from DRM/glamor/EGL hardware acceleration to software rendering in this headless virtual fixture. KWin and plasmashell remain alive and the tested APIs operate correctly.
- UPower/brightness/charge-threshold and Bolt messages reflect absent or unsupported virtual hardware. Their actual product claims belong to later power/hardware gates.
- WirePlumber probes Snap permission prompting and cannot connect because SupraLINUX intentionally has no Snap daemon; audio functionality is owned by C4.4 and is not inferred from this message.
- OBEX attempts to reach Evolution Data Server source-registry integration that is not present in this fixture. Bluetooth/OBEX behavior is owned by C4.5/C4.11 and remains pending there.
- Qt portal application-ID registration diagnostics appear for several session services. Portal behavior is explicitly owned by C4.6/C4.7 and remains pending; C4.1a makes no portal functionality claim.
- SDDM reports inability to write `utmpx` in the minimal CI guest. The Wayland Plasma session starts successfully and the two-boot functional test completes.
- During deliberate shutdown, the rfkill device emits a systemd transaction warning because poweroff is already queued. It occurs during teardown and does not leave a failed unit.
- Rootfs-composition logs include expected no-running-system-bus/service-start warnings while packages are installed inside the chroot. The actual guest subsequently boots and passes the runtime assertions.

None of these diagnostics is used to waive a requirement belonging to `AUR-KCM-002` or `AUR-KWIN-004`. Their owning later capabilities remain pending and must independently classify or resolve them when tested.

## Harness-defect chronology

Earlier C4.1a runs were intentionally not accepted:

1. run `33188910873`: session rebinding selected the persistent logind manager session instead of the graphical user session;
2. run `33190622750`: forced SDDM restart raced ActivityManager persistence and created an artificial session-environment problem;
3. run `33191735318`: guest behavior completed successfully, but the host marker counter treated `SESSION_RELOAD` as an additional `SESSION` because it matched by prefix;
4. run `33193325794`: exact marker matching exposed CRLF transport line endings and stopped after phase 1.

Each was classified as a harness/fixture defect before correction. No package was added or removed on the basis of those failures. The accepted run #5 includes the corrected two-clean-boot persistence design and exact CR-normalized marker comparison.

## Scope of acceptance

C4.1a proves only that, on the accepted Aurora Ubuntu 26.04 / Plasma 6.6 composition:

- Activities can be created, named, selected, rejected on invalid selection, persisted across a complete reboot, re-consumed by the new session, removed and restored to baseline;
- virtual desktops can be created, selected, reject an invalid current-desktop request without corrupting state, persist across a complete reboot, be consumed by the new KWin instance, be removed and restore the authoritative topology to baseline;
- KWin and plasmashell remain stable through the accepted second-boot functional sequence;
- no relevant failed units or crashes remain after the test.

It does not certify Baloo, appearance, shortcuts, effects, scripts, file associations, session options, screen locking or any other still-pending C4.1 row.

## Regression rule

This acceptance is invalidated when a later change can plausibly affect Activities or VirtualDesktopManager behavior, including relevant `kactivitymanagerd`, Plasma Workspace/Desktop, KWin, session persistence or product dependency/configuration changes.

Documentation-only changes and harness changes outside the accepted behavior do not reopen C1-C3 or C4.0.

## Verdict

Aurora C4.1a is formally accepted as **GREEN**.

- `AUR-KCM-002` = **PASS-C4**
- `AUR-KWIN-004` = **PASS-C4**

C4.1 remains **OPEN / ACTIVE**. No other C4.1 capability inherits PASS from this record.