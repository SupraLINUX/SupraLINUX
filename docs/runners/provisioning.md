# Authoritative KVM runner provisioning

Status: **repository implementation complete for current Phase 1 design; real KVM certification pending**  
Last reviewed: **2026-09-30**

The long-lived KVM/libvirt host is an infrastructure provider, not the build runner. The authoritative identity begins inside each disposable Ubuntu 26.04 JIT runner VM.

## Host boundary

Host bootstrap/preflight:

```text
scripts/provision-kvm-host.sh
scripts/check-kvm-host.sh
```

The supported recipe targets Ubuntu 26.04 amd64/x86_64, installs the declared KVM/libvirt/libguestfs toolchain, prepares state/evidence directories and group access, and validates nested KVM/readable-writable `/dev/kvm`, `qemu:///system`, required tools and active libvirt networking. It also prepares a private, SHA-256-verified copy of the currently booted root-only Ubuntu kernel for non-root supermin/libguestfs use. It does not silently modify BIOS/firmware, relax `/boot/vmlinuz-*` permissions, or forcibly reload KVM modules.

After any host kernel/module update, refresh this runtime before authoritative execution:

```bash
scripts/prepare-libguestfs-runtime.sh
scripts/check-kvm-host.sh
```

All host-side `virt-cat`, `virt-copy-out` and `virt-sysprep` calls run through `scripts/with-libguestfs-runtime.sh`, which fails closed if the prepared kernel copy, host-kernel metadata or module tree has drifted.

## Released Ubuntu source image

`scripts/fetch-ubuntu-26.04-cloud-image.sh` fetches the released Resolute amd64 cloud image into stable host storage:

```text
/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img
```

The directory retains `SHA256SUMS`, `SHA256SUMS.gpg` and provenance. Fetch-time verification uses Ubuntu's cloud-image keyring and verifies both detached signature and selected image SHA-256.

## Mandatory use-time re-verification

Before the golden builder inspects or uses the image, `scripts/verify-ubuntu-cloud-image-provenance.sh` re-runs `gpgv` over the retained signed metadata, derives the expected SHA-256 for the exact Resolute/amd64 filename, and requires both stored provenance and current image bytes to match the freshly signed value.

The builder retains this result as `source-image-verification.txt`. A mutable provenance file by itself is never a trust root.

## Golden-image build

Preferred path:

```bash
scripts/build-authoritative-runner-image.sh
```

The builder:

1. passes host preflight;
2. cryptographically re-verifies the local Ubuntu image before `qemu-img info` or overlay creation;
3. creates a temporary qcow2 overlay;
4. boots a KVM preparation VM using host CPU passthrough;
5. checks out the exact requested SupraLINUX commit;
6. provisions the Ubuntu 26.04 build/test toolchain and GitHub Actions runner whose published asset SHA-256 is verified;
7. builds the nested Resolute/amd64 `autopkgtest` QEMU image and records its hash;
8. removes runner registration/work state;
9. removes `/opt/supralinux-src` and records `source_checkout_removed=yes`;
10. powers the preparation VM off;
11. exports guest evidence;
12. runs explicit offline `virt-sysprep` identity/state cleanup;
13. flattens the overlay and runs `qemu-img check`;
14. writes final golden-image SHA-256/provenance including `source_image_provenance_verified=yes`.

Default output:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

Replacement requires explicit `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1`. Failed builds retain diagnostics and never publish a replacement golden image.

## Golden-image admission before JIT

A successfully built file is not automatically admitted forever. Before any JIT runner is created, the public entrypoint:

```text
scripts/run-kvm-jit-gate.sh
```

executes:

```text
scripts/check-golden-image-provenance.sh
```

The checker requires exactly one valid value for:

- `golden_image_sha256`;
- `source_image_sha256`;
- `source_commit` (full 40-hex SHA);
- `golden_input_fingerprint_schema=1`;
- `golden_input_digest` (64-hex SHA-256);
- `source_checkout_removed=yes`;
- `source_image_provenance_verified=yes`.

It recalculates the current golden-image SHA-256 and recomputes the versioned golden-input fingerprint for the checkout being certified. Modified bytes, duplicate/ambiguous fields, missing signed-source proof, missing source cleanup, an unsupported fingerprint schema, or any golden-relevant input drift fail closed. The original `source_commit` is retained for historical provenance; exact source-commit equality is not required when the current PR HEAD has an identical golden-input fingerprint.

Only after this gate passes does the wrapper delegate to `scripts/run-kvm-jit-gate-core.sh`, which implements the existing serialized libvirt/JIT workflow lifecycle.

Repository Policy functionally tests this gate without KVM, including negative cases for tampered golden bytes, missing signed-source proof, missing cleanup proof, duplicate hashes and truncated source commit evidence.

## GitHub Actions runner provenance

`scripts/install-actions-runner.sh` resolves the current stable `actions/runner` release, requires GitHub-published SHA-256 metadata for the Linux x64 asset, verifies the archive and records the selected tag/hash.

At authoritative runtime, `scripts/check-actions-runner-runtime.sh` queries the actual executable:

```text
/opt/actions-runner/bin/Runner.Listener --version
/opt/actions-runner/bin/Runner.Listener --commit
```

It does not use `run.sh` as a version evidence interface. Upstream `run.sh` delegates through `run-helper.sh`; the listener itself handles `--version` and `--commit` directly.

The runtime checker requires the effective semantic version to equal the verified golden release and requires a full 40-hex source commit. Version drift fails closed and instructs the operator to rebuild the golden image. Runtime evidence is retained as `actions-runner-runtime.txt` by both authoritative gates.

## Guest components

`scripts/provision-authoritative-runner-guest.sh` validates Ubuntu 26.04/KVM, installs declared build/test tools, subordinate IDs and KVM access, enables qemu-guest-agent, installs the verified runner and records provenance.

`scripts/prepare-autopkgtest-qemu-image.sh` requires usable nested KVM and builds:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

with real image SHA-256/provenance. Ubuntu 26.04 mounts `/tmp` as a memory-backed tmpfs, so the nested-image builder does not use the default `mktemp` location for its 20 GiB workspace. Guest provisioning installs `genisoimage` and creates runner-owned persistent work storage at `/var/lib/supralinux/autopkgtest/work`; a fail-closed workspace preflight rejects tmpfs/ramfs and insufficient free space before `autopkgtest-buildvm-ubuntu-cloud` starts.

The nested builder retains the upstream 2048 MiB VM RAM floor. Because the constrained golden-preparation VM previously had no swap and its kernel OOM-killed the nested QEMU process, image preparation now activates a 4096 MiB **temporary build-only swap file** on the persistent ext4 guest disk and records memory/swap evidence. The cleanup trap deactivates and removes it on both success and failure; the sealing step fails closed unless the temporary swap is absent, so the published golden image does not inherit preparation-only swap state. Nested guest I/O failures remain separately observable and are not reclassified as memory failures solely because an OOM was later observed.

`scripts/seal-authoritative-runner-image.sh` pre-seals runner/package state inside the guest. Clone identity is reset after shutdown by host-side offline `virt-sysprep`.

## Runtime JIT lifecycle

The golden image contains runner software but no persistent GitHub registration token/PAT/JIT config and no temporary SupraLINUX checkout.

After golden admission, `scripts/run-kvm-jit-gate-core.sh` creates a fresh overlay VM, requests repository `generate-jitconfig`, injects it into guest `/run`, launches the runner non-root, waits until it is online, applies one controlled PR label, binds one new workflow run for the exact PR head SHA, exports diagnostics/evidence and destroys writable state.

Required labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

Controlled pre-merge labels:

```text
ci:runner-contract
ci:authoritative-package-proof
ci:frameworks-sample-proof
```

Both host and workflows refuse fork PRs. Do not add these labels until the matching disposable JIT runner is actually online.

## Certification sequence

A golden image and Phase 1 remain **pending** until real evidence establishes:

1. host preflight PASS;
2. signed Ubuntu source-image fetch verification and real source SHA-256;
3. use-time GPG/SHA-256 re-verification PASS;
4. golden build from an exact source commit;
5. golden admission PASS against current bytes/provenance;
6. effective Actions runner provenance PASS;
7. temporary source checkout absent from the golden image;
8. offline sysprep/flatten/qcow2-check evidence and final golden SHA-256;
9. nested `autopkgtest` image SHA-256;
10. `runner-contract.yml` PASS on a disposable JIT KVM guest, including real nested-KVM probe;
11. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest, including clean `sbuild` and KVM-only `autopkgtest/QEMU`;
12. `authoritative-frameworks-sample-proof.yml` PASS on a third disposable JIT KVM guest, rebuilding canonical KArchive `6.30.0-0supralinux4` with exact ECM `6.30.0-0supralinux3` and retaining package/test/ABI/consumer evidence;
13. retained workflow artifacts plus host/runner diagnostics.

Until the remaining real VMs execute, no authoritative runner/package PASS or real golden-image hash is claimed.


### Frameworks lane sample

The generic authoritative package proof certifies the KVM/sbuild/autopkgtest machinery, but it is intentionally based on the synthetic `supralinux-build-test` package. Before KWin, Plasma or session work can use the lane as release-relevant evidence, SupraLINUX requires one real KDE Framework sample.

The selected sample is **KArchive 6.30.0-0supralinux4** because it is a canonical Tier 1 PASS with a small dependency surface and real upstream tests. The gate reuses the retained canonical source package from workflow `34884764702`, artifact `10364726750`, and the exact ECM predecessor `6.30.0-0supralinux3` from workflow `34694951158`, artifact `10298635300`.

Run it only after the first two gates pass:

```bash
scripts/run-kvm-jit-gate.sh runner-contract
scripts/run-kvm-jit-gate.sh authoritative-package-proof
scripts/run-kvm-jit-gate.sh frameworks-sample-proof
```

The sample is a certification run, not a new canonical KArchive package attempt: it records `package_state_effect=none`.


## Live certification state

The current authoritative runner lifecycle is tracked in `manifests/authoritative-kvm-certification.json` and validated by Repository Policy.

The manifest deliberately separates hosted Frameworks completion from real KVM certification. The live host contract is now PASS after real-host recertification of KVM/libvirt, the private non-root libguestfs runtime and the synthetic golden-preparation lifecycle; earlier host evidence remains retained as historical evidence. Golden-image admission, runner-contract, synthetic package proof and KArchive Frameworks sample remain pending real evidence. Until the final Frameworks sample is PASS, `desktop_release_relevant_authorized=false` and Plasma/KWin/session release-relevant execution remains locked.

This live-state manifest is not historical evidence. Real KVM workflow IDs, image hashes and retained artifacts are added only after those executions occur.


### One-command host certification

Once the KVM/libvirt host has been provisioned and the repository checkout is exactly the open PR head, the supported full certification entrypoint is:

```bash
SUPRALINUX_GITHUB_TOKEN=... \
SUPRALINUX_RUNNER_GROUP_ID=... \
scripts/run-authoritative-kvm-certification.sh
```

The orchestrator fails closed unless the local checkout is clean and its HEAD exactly matches the PR head. It validates the host, fetches or verifies the signed Ubuntu 26.04 source image, then admits an existing golden only when its versioned golden-input fingerprint matches the current PR HEAD; otherwise an explicit rebuild is required. A new golden is built from the current PR commit. It then runs the three disposable JIT gates in strict order:

1. `runner-contract`;
2. `authoritative-package-proof`;
3. `frameworks-sample-proof`.

An existing golden image is never replaced implicitly. If it is stale or invalid, replacement requires explicit `SUPRALINUX_REBUILD_GOLDEN=1`. The previous image is still handled by the golden builder's preservation logic.

The run writes a self-contained evidence bundle under `/var/lib/supralinux/evidence/authoritative-certification/` by default, including host preflight, source/golden provenance, gate host evidence, exact GitHub workflow run IDs and `certification-result.json`.

The orchestrator deliberately does **not** run `git commit` or `git push`, does not update canonical package state, and never authorizes stable publication. Real evidence must be reviewed and then consumed by the live-state lifecycle separately.
