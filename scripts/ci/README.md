# Aurora CI helpers

These scripts implement the current Aurora validation layers.

## KDE Stack Qualification

- `validate-kde-stack-source-manifests.sh` validates the pinned official Plasma/Frameworks source manifests.
- `validate-kde-stack-roots.py` verifies that every direct `supralinux-desktop` Depends/Recommends root is classified against the candidate release sets or the Ubuntu/Gear policy boundary.
- `prepare-kde-stack-apt-metadata.sh` prepares isolated snapshot-only APT metadata: Resolute binary+source metadata and Stonking source-only metadata.
- `generate-kde-build-closure.py` is the canonical provider-aware strict KSQ-0 transitive Build-Depends resolver. Certification does not use an allow-unresolved mode.
- `audit-kde-stack-source-selections.sh` verifies exact external source inputs, pinned hashes and the certified `kwallet-pam` PAM packaging invariants.
- `prepare-ksq-1-source.py` converts a certified packaging base to the deterministic `~supra26.04.1` candidate version and applies only adaptations declared in `tests/kde-stack/ksq-1-packaging-adaptations.tsv`. For `kwallet-pam`, compat 14→13 restores explicit relationship substvars needed to preserve dependency-generation semantics. For `kf6-syntax-highlighting`, the declared quilt patch makes Jinja grammar traversal deterministic so Python hash randomization cannot reorder the embedded syntax QRC.
- `fetch-prepare-ksq-1-source.sh` fetches the exact certified source input and emits the prepared source package plus source-preparation evidence, including the exact applied adaptation IDs/count and certified Build-Depends override count.
- `prepare-ksq-1-build-environment.sh` creates the clean Resolute amd64 buildd tarball from the pinned Ubuntu snapshot.
- `prepare-ksq-1-runner.sh` revalidates KSQ-0, source selections and the pinned build environment on each fresh checkpoint runner.
- `build-ksq-1-bootstrap.sh` builds the first four certified DAG nodes and retains relocatable bootstrap evidence.
- `build-ksq-1-range.sh START END` builds an ordered KSQ-1 DAG range with `sbuild --chroot-mode=unshare`, no build-time network, and accumulated candidate DEBs supplied through `--extra-package`. It enables `--resolve-alternatives` because Debian Build-Depends semantics include valid `A | B` alternatives. The APT uninstallable-dependency explainer is enabled for diagnosis. On failure it records the first failed source/order, `.build`, `.buildinfo`, `.changes`, any partial DEB/DDEB output, hashes and the successful DEBs already produced in that checkpoint before exiting non-zero.
- `validate-ksq-1-kwallet-pam.sh` validates the rebuilt KWallet PAM binary dependency metadata and installs the candidate packages in a disposable Resolute environment before invoking the PAM registration contract.
- `validate-kwallet-pam-installation.sh [rootfs]` requires `pam_kwallet5.so` to be registered in both `common-session` and `common-auth`. Package-level installation does not by itself certify live graphical-session auto-unlock.
- `validate-ksq-1-full.py` validates the completed 101-source build manifests, binary ownership/version evidence, accumulated hashes, exactly 101 prepared-source metadata records, the exact two-ID KSQ-1 adaptation boundary and the KWallet package-level gate. It intentionally leaves reproducibility and full KSQ-1 certification marked `no`.
- `validate-ksq-1-reproducibility.py` validates complete independent byte-identity coverage after the authoritative full build. For unaffected sources it first requires exact prepared-source identity before comparing candidate/reference DEBs. Node 29 plus the five dependency descendants invalidated by its source patch (68, 81, 99, 100, 101) require dedicated independent rebuild hashes instead of pre-patch reference binaries.

The full KSQ-1 workflow is `.github/workflows/ksq-1-full-builds.yml`. It builds 001–020, 021–040, 041–060, 061–080 and 081–101 in fresh Resolute runners, transports only explicit binary checkpoint artifacts between jobs, and preserves checkpoint evidence with `if: always()` so the first failure remains diagnosable.

Syntax Highlighting reproducibility has three evidence layers:

- `.github/workflows/ksq-1-syntax-repro-investigation.yml` reproduces the original `set.pop()` hash-seed-dependent Jinja ordering and proves deterministic traversal stabilizes generator order without changing generated XML content;
- `.github/workflows/ksq-1-syntax-repro-patched-build.yml` built the patched source twice against certified nodes 1–28 and all six DEBs plus three DDEBs were byte-identical; its historical red conclusion came after those comparisons from a later evidence-copy bug;
- `.github/workflows/ksq-1-syntax-repro-artifact-validation.yml` independently validates that binary artifact;
- `.github/workflows/ksq-1-syntax-materialization-identity.yml` proves the currently materialized `.dsc`, Debian source delta, quilt patch and series are byte-identical to the source used by the proven two-build experiment before that evidence may be reused.

Node-40 investigation established why alternative resolution is mandatory: `kf6-kfilemetadata` declares `libpostproc-dev | hello`; the original sbuild invocation considered only the first alternative and failed because `libpostproc-dev` is unavailable in the pinned Resolute archive. A dedicated validation proved that enabling normal alternative resolution selects `hello` and builds the package without changing package sources or widening the Ubuntu platform boundary.

Canonical KSQ-0 evidence is documented in `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`, current KSQ-1 status in `docs/KDE_STACK_QUALIFICATION.md`, and override ownership in `docs/KDE_STACK_OVERRIDES.md`.

## Historical/current product validation helpers

- `build-packages.sh` builds the current SupraLINUX development DEB packages without signing them.
- `validate-apt-resolution.sh` verifies that the local package set resolves on Ubuntu 26.04 and that the default SupraLINUX Snap policy prevents Snap components from becoming installable candidates.
- `validate-clean-rootfs.sh` creates an isolated Ubuntu 26.04 `debootstrap` rootfs, installs the SupraLINUX policy/base/desktop packages for real, runs `apt-get check`, verifies required desktop integration packages are installed, and rejects Ubuntu Desktop, Kubuntu Desktop, GNOME Shell and Snap components.

The CI scripts must remain non-destructive with respect to the runner host. Dependency validation should use isolated APT state or simulation unless a test explicitly requires an isolated disposable environment. Real product package installation is confined to disposable rootfs/VM environments rather than the GitHub runner host.
