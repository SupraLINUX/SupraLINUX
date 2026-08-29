# Aurora C4.1b File Search — historical investigation record

Status: **INCONCLUSIVE / NOT ACCEPTED — KDE 6.6.6 historical baseline**

This record preserves the last File Search/Baloo investigation performed before Aurora paused C4.1 for KDE Stack Qualification. It is evidence about the historical Ubuntu KDE 6.6.6 / Frameworks 6.24 baseline only. It is neither a `PASS-C4` nor a confirmed product failure for the future KDE stack.

## Scope

Capability: `AUR-KCM-003` — File Search / Baloo.

Relevant historical implementation:

- Plasma 6.6.6 File Search KCM expects to start `baloo_file` by executable name through `QStandardPaths::findExecutable()` when indexing is enabled;
- Ubuntu 26.04 `baloo6 6.24.0-0ubuntu1` installs the real daemon under KDE's multiarch libexec path rather than a normal session `PATH` directory;
- SupraLINUX commit `7d9586ae2023c6281c0385b1987c2ed19f004084` added a narrowly scoped `/usr/bin/baloo_file` compatibility launcher in `supralinux-settings` that resolves and `exec`s the real `baloo6` daemon.

The compatibility launcher remains subject to KSQ-8. A newer KDE stack must reproduce the original user-visible path before deciding to keep or remove it.

## Run 1 — original packaging mismatch reproduced

Workflow run: `33220350814`  
HEAD: `17e7b104a738f48939dba7f2f90bd6ead707ab0b`  
Conclusion: **FAIL at `SESSION`**  
Artifact: `aurora-c4-1b-baloo-diagnostics-33220350814-1`  
Artifact ID: `9705030060`  
Digest: `sha256:541dc1d18219adc7a780216e149908feca9c07a611dcdb84f4e9615173bdf898`

The real Plasma session PATH was recorded as:

```text
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
```

and the test recorded no resolvable `baloo_file` executable. The installed systemd user unit instead pointed directly to the package-private libexec daemon. This was the evidence that justified the compatibility launcher; the test was not weakened to ignore the KCM executable-resolution path.

## Run 2 — launcher fixed executable resolution; later test became inconclusive

Workflow run: `33221026223`  
HEAD: `7d9586ae2023c6281c0385b1987c2ed19f004084`  
Conclusion: **FAIL at `INDEXING`**  
Artifact: `aurora-c4-1b-baloo-diagnostics-33221026223-1`  
Artifact ID: `9705363268`  
Digest: `sha256:35f7fdb6060a4707b53b4d33d51ddc8ddbf288ce360f160eb8b686d921c69643`

The second run proved that the original executable-resolution condition had changed as intended:

```text
baloo_exe=/usr/bin/baloo_file
```

The run passed `SESSION`, `BASELINE`, `ENABLE` and `INCLUDE_ROOT`, registered `org.kde.baloo`, and reached the normal scheduler indexing stage. The three controlled fixture files then remained `status: failed` / `indexing: content`, and the journal recorded repeated abort/core-dump events from Ubuntu's real:

```text
/usr/lib/x86_64-linux-gnu/libexec/kf6/baloo_file_extractor
```

with the stack reaching `QGuiApplication` initialization.

The same HEAD independently passed the relevant surrounding gates, including package validation, clean-rootfs validation, C1, C2, C3, C4.0, C4.1a and the C4.1b Baloo preflight. Therefore the compatibility launcher itself did not cause a broad boot/session/composition regression in those gates.

## Harness-fidelity defect discovered

Run 2 must **not** be classified as a confirmed Baloo product defect without another reproduction.

The guest harness helper `run_user()` explicitly reconstructs only these session-related variables:

- `HOME`
- `USER`
- `LOGNAME`
- `XDG_RUNTIME_DIR`
- `DBUS_SESSION_BUS_ADDRESS`

The KCM-equivalent launch then adds the Plasma session `PATH`, but the harness does not copy the complete environment of the real Plasma process, including graphical variables such as `DISPLAY` and `WAYLAND_DISPLAY`, before spawning `baloo_file`.

That distinction matters because the failed child process aborts while initializing `QGuiApplication`. A real KCM-started process inherits the graphical Plasma session environment. The historical harness therefore ceased to be a sufficiently faithful reproduction once it advanced beyond executable resolution.

Classification for Run 2:

> **HARNESS / SESSION-ENVIRONMENT FIDELITY DEFECT — product result inconclusive.**

This classification does not claim that Baloo 6.24 is defect-free. It says only that this run cannot distinguish a product extractor failure from an artifact of the test launch environment.

## Historical capability state

`AUR-KCM-003` remains **not certified**. No `PASS-C4` is granted.

The evidence does establish two useful historical facts:

1. Ubuntu's Plasma 6.6.6/Baloo packaging combination did not expose `baloo_file` through the real Plasma session PATH expected by the KCM enable path.
2. The SupraLINUX compatibility launcher made that executable resolvable and allowed the test to progress beyond the original failure point without breaking the surrounding baseline gates.

It does **not** establish successful filename/content indexing, exclusion behavior, reboot persistence, disable/re-enable lifecycle or cleanup.

## Required treatment under KDE Stack Qualification

When KSQ-8 reaches the Baloo integration delta:

1. test the candidate KDE stack without assuming the compatibility launcher is still required;
2. reproduce the actual File Search enable/disable path using either the real KCM action or a launcher that inherits the complete graphical session environment;
3. verify the process ultimately executes the package-owned Baloo backend;
4. if executable resolution is fixed by new upstream/distribution packaging, remove the SupraLINUX launcher and prove the workflow without it;
5. if the mismatch remains, retain the narrow launcher only after re-proving the defect and the fix;
6. only then resume the full indexing/exclusion/persistence/cleanup C4.1 contract.

No additional package change is justified by Run 2 alone.
