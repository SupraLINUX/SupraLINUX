# Build, CI and promotion architecture

Status: **active architecture**  
Last reviewed: **2026-09-17**

## Build semantics

SupraLINUX uses a DAG-guided hybrid build strategy. Every attempted node/gate ends as `PASS` or `FAIL`; a node not attempted because a prerequisite or execution capability is unavailable is `BLOCKED`. `BLOCKED` is never counted as `FAIL`.

Campaigns resolve the selected manifest, construct the dependency DAG, build every possible independent node by topological level, expose only PASS artifacts to dependents, preserve evidence and rerun the complete campaign before promotion.

## Repository mutation boundary

Repository source state is assembled **before** CI. GitHub Actions validates, builds, tests and produces evidence; it is not the normal mechanism for materializing or editing the repository it is meant to validate.

A logical multi-file change is prepared as one coherent transaction and published as one atomic Git commit. The preferred remote-write path is `blob -> tree -> commit -> ref`, based on the current branch tree. The branch HEAD is rechecked before publication and is never force-updated to hide concurrent changes.

Temporary materializer/promoter workflows are not the normative model for subsequent work. The complete rationale and operational rules are recorded in `docs/decisions/repository-mutation-strategy-2026-09-17.md`.

## Pull-request CI routing

Ordinary hosted pull-request CI is admitted through `.github/workflows/pr-ci-router.yml`. The router is the single subscriber for `pull_request` lifecycle events `opened`, `synchronize` and `reopened` across the migrated hosted package/reference/provider/diagnostic lanes.

For a synchronization, the router evaluates the exact `${{ github.event.before }} -> ${{ github.event.after }}` delta. For opened/reopened PRs it compares base SHA to head SHA. A documentation-only delta (`docs/**` and/or `README.md`) stops after the router planning job; the 18 reusable hosted lanes remain skipped. A non-documentation delta may enter those lanes, where the existing lane-specific scope detectors still decide which expensive work is actually required.

The routed workflows expose `workflow_call` and retain `workflow_dispatch`; workflows that already ran on `push: main` keep that trigger. They do not independently listen to ordinary PR lifecycle events. Controlled authoritative workflows triggered by labels remain separate from this router.

The router also uses per-PR concurrency with `cancel-in-progress: true`. A newer synchronization cancels an obsolete router execution for the same PR instead of allowing stale package/reference work to continue.

This architecture is policy-enforced by `scripts/validate_repository.py` and, for the Qt lane, `scripts/validate_qt_provider.py`. Live verification on 2026-09-17 established:

- superseded router run `35178935759`: **cancelled** automatically;
- Repository Policy run `35181296924`: **PASS**, 30/30 steps;
- documentation-only router run `35181360370`: **PASS**, one planning job PASS and 18 reusable lanes skipped;
- matching Repository Policy run `35181360187`: **PASS**, 30/30 steps.

Detailed semantics and historical evidence are recorded in `docs/ci-event-delta-scope.md` and `docs/decisions/pr-ci-routing-2026-09-17.md`.

## Hosted preflight lane

GitHub-hosted `ubuntu-26.04` is non-authoritative. It performs repository/manifest policy, static checks and clean package-build preflight. `ubuntu-latest` is forbidden.

The package preflight creates a fresh Resolute `buildd` rootfs with `mmdebstrap`, builds through `sbuild --chroot-mode=unshare`, and preserves `.deb`, `.changes`, `.buildinfo`, hashes and logs. It intentionally does not claim the authoritative system-test gate.

The **consumer-runtime closure** smoke must validate the built package's actual runtime dependency closure rather than inheriting whatever libraries happen to exist on the hosted runner. For package lanes using the Batch 6 pattern, the exact locally built `.deb` set is installed through APT with `--no-install-recommends`; APT resolves external `Depends`, `apt-get check` must pass, and every locally built package is verified at the exact built Debian version. Consumer CMake discovery still uses the extracted local artifacts, and the built runtime library remains first in `LD_LIBRARY_PATH`, so Ubuntu supplies external dependencies without replacing the SupraLINUX artifact under test.

A shared runner change is itself a build input for every node using that runner. Therefore a retained `PASS` node may be intentionally revalidated when shared runner semantics change; its previous PASS evidence is preserved rather than rewritten or silently scope-skipped.

Expensive hosted package work is gated on the actual PR event delta. Documentation-only synchronizations stop at the centralized router before entering package/reference/provider lanes. For relevant deltas, each invoked lane still applies its own event-delta scope before expensive execution.

Repository Policy requires:

- immutable `actions/checkout` SHA `3d3c42e5aac5ba805825da76410c181273ba90b1`;
- Bash syntax validation for all `scripts/*.sh`;
- Ubuntu 26.04 ShellCheck (`shellcheck -e SC1091 scripts/*.sh`);
- deterministic KVM-QEMU wrapper functional testing;
- cryptographic Ubuntu source-image functional testing;
- effective GitHub Actions runner provenance functional testing;
- golden-image provenance functional testing;
- repository architecture/invariant validation;
- centralized PR-router/reusable-lane invariants;
- live Ubuntu/Qt candidate validation.

`SC1091` is excluded only for intentional runtime system sources such as `/etc/os-release`; all other ShellCheck diagnostics are blocking.

## Authoritative KVM/JIT lane

Release-relevant evidence is produced inside disposable self-hosted Ubuntu 26.04 KVM VMs. Required labels are:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `kvm`, `ephemeral`.

The host requests a fresh repository-scoped JIT configuration, injects it into guest tmpfs, executes one controlled job, exports diagnostics and destroys writable VM state. Fork PRs are refused before self-hosted execution.

Host orchestration is serialized. It rejects pre-existing queued/active authoritative workflows before creating a runner, snapshots workflow IDs before the trigger, and binds evidence to exactly one newly-created workflow run for the exact PR head SHA. Ambiguous attribution fails closed.

The public host entrypoint is `scripts/run-kvm-jit-gate.sh`. Before it delegates to `scripts/run-kvm-jit-gate-core.sh`, it validates the golden image with `scripts/check-golden-image-provenance.sh`. Therefore JIT orchestration cannot start from a golden image whose current bytes, source commit, source cleanup or signed-source verification evidence fail policy.

## Effective Actions runner provenance

The golden builder verifies the GitHub-published SHA-256 for the selected stable `actions/runner` asset and records the release tag/hash. Because JIT configuration does not expose a supported `disableupdate` registration input, authoritative runtime also verifies the effective runner.

`scripts/check-actions-runner-runtime.sh` queries the actual `bin/Runner.Listener` binary directly using `--version` and `--commit`. It requires:

- exactly one verified runner `tag` and `asset_sha256` in golden provenance evidence;
- a semantic runtime version matching the verified golden release;
- a full 40-hex runtime source commit;
- explicit runtime evidence `runtime_matches_verified_version=yes`.

A version mismatch fails closed and requires rebuilding the golden image. The checker deliberately does not derive version/commit from `run.sh`: upstream `run.sh` delegates through `run-helper.sh`, while `Runner.Listener` itself handles `--version`/`--commit` directly before normal run mode.

Both `runner-contract.yml` and the authoritative package proof execute this runtime check and retain `actions-runner-runtime.txt`.

## Real nested-KVM gate

A `kvm` label or `/dev/kvm` device alone is not certification. `scripts/check-nested-kvm-runtime.sh` must successfully keep a minimal QEMU process alive under:

```text
qemu-system-x86_64 -accel kvm -cpu host ... -S
```

An early QEMU exit is FAIL. Both the runner contract and authoritative package proof execute this runtime probe.

## Deterministic system-test virtualization

`autopkgtest-virt-qemu` can operate without hardware acceleration, so SupraLINUX does not let it choose acceleration implicitly.

The authoritative proof passes `scripts/qemu-kvm-required.sh` through `--qemu-command` and pins `--qemu-architecture=x86_64`. The wrapper executes QEMU with `-accel kvm` and has no TCG fallback. Its SHA-256 is retained as evidence.

Inside the runner VM:

```text
fresh sbuild/unshare
└── .deb + .changes + .buildinfo + hashes

autopkgtest/QEMU
└── KVM-only QEMU command wrapper
    └── nested Ubuntu 26.04 KVM test VM
```

Build artifacts are captured before runtime tests so a later test failure cannot erase build-PASS evidence.

## Ubuntu runner source-image integrity

Source-image trust is checked twice against the same Ubuntu signing authority.

### Fetch-time verification

`scripts/fetch-ubuntu-26.04-cloud-image.sh` downloads the released Resolute amd64 cloud image together with `SHA256SUMS` and `SHA256SUMS.gpg`, verifies the signature with Ubuntu's cloud-image keyring, derives the expected image SHA-256 from the signed metadata, verifies the downloaded bytes, and stores metadata/provenance under stable host storage.

### Use-time cryptographic re-verification

Before the golden builder even asks `qemu-img` to inspect the source image, `scripts/verify-ubuntu-cloud-image-provenance.sh` re-runs `gpgv`, derives the expected hash from freshly verified Ubuntu metadata, and requires provenance and actual bytes to match that signed value.

Repository Policy tests this logic with an ephemeral GPG signing key and real detached signatures, including negative cases for tampering and forged mutable provenance.

## Golden runner-image chain and admission gate

```text
released Ubuntu Resolute cloud image
-> fetch-time signed checksum verification
-> use-time GPG signature + SHA-256 re-verification
-> temporary qcow2 preparation overlay
-> Ubuntu 26.04 KVM preparation VM
-> exact SupraLINUX source commit checkout
-> verified runner/toolchain provisioning
-> nested autopkgtest image creation
-> runner pre-seal + temporary source checkout removal
-> VM poweroff
-> offline virt-sysprep identity cleanup
-> qemu-img flatten + check
-> standalone golden qcow2 + SHA-256/provenance
-> golden provenance admission gate
-> disposable JIT overlay
```

`scripts/check-golden-image-provenance.sh` admits a golden image only when it has exactly one valid `golden_image_sha256`, `source_image_sha256`, `source_commit`, `source_checkout_removed=yes` and `source_image_provenance_verified=yes`, and the current golden bytes hash to the recorded SHA-256. Ambiguity or tampering is FAIL.

Existing golden images are never replaced without explicit `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1` opt-in.

## Evidence contract

Important build/test evidence includes, where applicable: source/version/commit and hashes; dependency/configuration manifests; complete logs; `.deb`, `.changes`, `.buildinfo`; host preflight; signed Ubuntu source metadata and use-time verification; Actions runner verified release/digest plus effective runtime version/commit; golden admission evidence; nested test-image hash; offline sysprep/qcow2 validation; final golden-image hash/provenance; nested-KVM probe; QEMU-wrapper hash; exact PR head and workflow run ID; runner/VM diagnostics; terminal state.

Hashes/results are evidence and must never be invented or copied from unrelated runs.

## Promotion model

`upstream stable -> SupraLINUX packaging -> authoritative clean build -> authoritative tests -> incoming/staging -> candidate -> stable`

Repository publication/signing remains separate from compilation. Builders do not require the stable repository private signing key.

## Initial gates

Repository/manifest validation; Bash syntax; ShellCheck; QEMU-wrapper test; signed Ubuntu source-image test; effective Actions runner provenance test; golden-image provenance test; source integrity; centralized PR event-delta routing; hosted clean-build preflight; host KVM/nested preflight; verified source image; use-time cryptographic source re-verification; golden-image build/provenance; golden admission; authoritative JIT/KVM runner certification; real nested-KVM runtime probe; authoritative `sbuild`; package metadata; `autopkgtest/QEMU` through KVM-only wrapper; DAG consistency; install/upgrade tests; KDE session/runtime smoke tests; Ubuntu application compatibility tests for replaced shared libraries; repository publication verification.

Existing gates cannot be removed silently: implementation, machine-readable policy and documentation must change together.
