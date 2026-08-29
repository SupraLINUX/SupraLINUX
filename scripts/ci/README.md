# Aurora CI helpers

These scripts implement the current Aurora validation layers.

## KDE Stack Qualification

- `validate-kde-stack-source-manifests.sh` validates the pinned official Plasma/Frameworks source manifests.
- `validate-kde-stack-roots.py` verifies that every direct `supralinux-desktop` Depends/Recommends root is classified against the candidate release sets or the Ubuntu/Gear policy boundary.
- `prepare-kde-stack-apt-metadata.sh` prepares isolated snapshot-only APT metadata: Resolute binary+source metadata and Stonking source-only metadata.
- `generate-kde-build-closure.py` is the canonical provider-aware strict KSQ-0 transitive Build-Depends resolver. Certification does not use an allow-unresolved mode.
- `audit-kde-stack-source-selections.sh` verifies exact external source inputs, pinned hashes and the certified `kwallet-pam` PAM packaging invariants.
- `prepare-ksq-1-source.py` converts a certified packaging base to the deterministic `~supra26.04.1` candidate version and applies only declared KSQ packaging adaptations. For `kwallet-pam`, compat 14→13 also restores the explicit relationship substvars required to preserve dependency-generation semantics.
- `fetch-prepare-ksq-1-source.sh` fetches the exact certified source input and emits the prepared source package plus source-preparation evidence.
- `prepare-ksq-1-build-environment.sh` creates the clean Resolute amd64 buildd tarball from the pinned Ubuntu snapshot.
- `prepare-ksq-1-runner.sh` revalidates KSQ-0, source selections and the pinned build environment on each fresh checkpoint runner.
- `build-ksq-1-bootstrap.sh` builds the first four certified DAG nodes and retains relocatable bootstrap evidence.
- `build-ksq-1-range.sh START END` builds an ordered KSQ-1 DAG range with `sbuild --chroot-mode=unshare`, no build-time network, and accumulated candidate DEBs supplied through `--extra-package`. It enables `--resolve-alternatives` because Debian Build-Depends semantics include valid `A | B` alternatives. The APT uninstallable-dependency explainer is enabled for diagnosis. On failure it records the first failed source/order, `.build`, `.buildinfo`, `.changes`, any partial DEB/DDEB output, hashes and the successful DEBs already produced in that checkpoint before exiting non-zero.
- `validate-ksq-1-kwallet-pam.sh` validates the rebuilt KWallet PAM binary dependency metadata and installs the candidate packages in a disposable Resolute environment before invoking the PAM registration contract.
- `validate-kwallet-pam-installation.sh [rootfs]` requires `pam_kwallet5.so` to be registered in both `common-session` and `common-auth`. Package-level installation does not by itself certify live graphical-session auto-unlock.
- `validate-ksq-1-full.py` validates the completed 101-source build manifests, binary ownership/version evidence, accumulated hashes and the KWallet package-level gate before later KSQ-1 reproducibility certification.

The full KSQ-1 workflow is `.github/workflows/ksq-1-full-builds.yml`. It builds 001–020, 021–040, 041–060, 061–080 and 081–101 in fresh Resolute runners, transports only explicit binary checkpoint artifacts between jobs, and preserves checkpoint evidence with `if: always()` so the first failure remains diagnosable.

Node-40 investigation established why alternative resolution is mandatory: `kf6-kfilemetadata` declares `libpostproc-dev | hello`; the original sbuild invocation considered only the first alternative and failed because `libpostproc-dev` is unavailable in the pinned Resolute archive. A dedicated validation proved that enabling normal alternative resolution selects `hello` and builds the package without changing package sources or widening the Ubuntu platform boundary.

Canonical KSQ-0 evidence is documented in `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`, current KSQ-1 status in `docs/KDE_STACK_QUALIFICATION.md`, and override ownership in `docs/KDE_STACK_OVERRIDES.md`.

## Historical/current product validation helpers

- `build-packages.sh` builds the current SupraLINUX development DEB packages without signing them.
- `validate-apt-resolution.sh` verifies that the local package set resolves on Ubuntu 26.04 and that the default SupraLINUX Snap policy prevents Snap components from becoming installable candidates.
- `validate-clean-rootfs.sh` creates an isolated Ubuntu 26.04 `debootstrap` rootfs, installs the SupraLINUX policy/base/desktop packages for real, runs `apt-get check`, verifies required desktop integration packages are installed, and rejects Ubuntu Desktop, Kubuntu Desktop, GNOME Shell and Snap components.

The CI scripts must remain non-destructive with respect to the runner host. Dependency validation should use isolated APT state or simulation unless a test explicitly requires an isolated disposable environment. Real product package installation is confined to disposable rootfs/VM environments rather than the GitHub runner host.
