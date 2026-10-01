# KVM/libvirt host orchestration

Status: **host PASS; golden image PASS; runner-contract PASS; authoritative package proof next**  
Last reviewed: **2026-10-01**

The long-lived host is an infrastructure provider only. It is not a SupraLINUX build runner and must not be treated as release evidence. Its job is to provide KVM/libvirt, build the sealed Ubuntu 26.04 golden runner image, create one disposable runner guest per authoritative GitHub Actions job, preserve evidence, and destroy writable VM state afterwards.

## Host bootstrap and preflight

The supported host recipe currently targets Ubuntu 26.04 amd64/x86_64:

```bash
scripts/provision-kvm-host.sh
# open a new login session
scripts/check-kvm-host.sh
```

The bootstrap installs KVM/QEMU, libvirt, `virt-install`, libguestfs and support tools; configures `kvm`/`libvirt` access; prepares `/var/lib/supralinux` state directories; and starts the selected libvirt network when available.

It does **not** alter firmware/BIOS settings or forcibly reload KVM modules. The read-only preflight requires visible CPU virtualization, usable `/dev/kvm`, nested KVM, required groups/tools (including libguestfs and `flock`), working `qemu:///system`, an active libvirt network, and a prepared private libguestfs kernel runtime matching the currently booted kernel and module tree.

Ubuntu 26.04 keeps `/boot/vmlinuz-*` root-only on this host. SupraLINUX therefore does not relax `/boot` permissions and does not run all libguestfs operations as root. `scripts/prepare-libguestfs-runtime.sh` makes a SHA-256-verified `0600` copy owned by the orchestration user under `/var/lib/supralinux/images/libguestfs-runtime/<kernel-version>/`. `scripts/with-libguestfs-runtime.sh` validates recorded kernel metadata, the private-copy hash and the `modules.dep` hash, then exports the supported supermin/libguestfs environment before running the requested tool. After a host kernel/module update, rerun the preparation script before authoritative work.

## Verified Ubuntu source image

Fetch the released Resolute image with:

```bash
scripts/fetch-ubuntu-26.04-cloud-image.sh
```

Signed checksum metadata and the selected image SHA-256 are verified before admission. The default source image is kept in stable host storage:

```text
/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img
```

This is deliberately outside the developer checkout because the file is used as a backing image by `qemu:///system` during golden preparation.

## Golden image build

Run:

```bash
scripts/build-authoritative-runner-image.sh
```

The builder requires host preflight PASS and verified source-image provenance. It creates a preparation overlay, boots a KVM guest with host CPU passthrough, checks out the exact requested SupraLINUX commit, provisions the toolchain/runner, creates the nested `autopkgtest` image, seals runner state, removes the temporary source checkout, powers off, exports evidence, applies explicit offline `virt-sysprep`, flattens the overlay, runs `qemu-img check` and records the final golden-image SHA-256/provenance.

Golden provenance also records a versioned SHA-256 fingerprint of the repository inputs that actually define the golden image. The build commit remains immutable historical provenance; admission against a later PR HEAD is allowed only when that HEAD has the same golden-input fingerprint. State/evidence/documentation-only commits therefore do not force image churn, while a change to any declared golden input fails closed and requires an explicit rebuild.

For the system libvirt connection, the preparation directory remains private to the invoking user while its group is set to the effective libvirt QEMU group. The directory grants group traversal only (`0710`) and the writable qcow2 grants owner/group read-write only (`0660`). The builder records these modes and identities in `libvirt-storage-access.txt`; it does not make the build tree world-readable or world-writable.

Default output:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

Existing golden images are not replaced unless `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1` is explicitly supplied. Failed builds preserve diagnostic state and do not publish a replacement image. The preparation launch uses `virt-install --noreboot` because cloud-init deliberately powers the guest off when provisioning completes; the builder requires that domain to remain shut off before any offline evidence extraction or sysprep begins.

After two consecutive `INFRA_INVALID` incidents in the golden-preparation mechanism, full retries are frozen until the real-host synthetic lifecycle preflight passes:

```bash
scripts/check-golden-preparation-lifecycle.sh
```

That preflight reuses the verified Ubuntu source image but performs no package build: it exercises the same scoped libvirt storage permissions, boots a minimal KVM guest, writes a guest marker, powers off, requires the domain to remain `shut off`, retains evidence, and cleans up the disposable VM. Its writable state lives under the already provisioned operator-owned `/var/lib/supralinux/golden-builds/lifecycle-preflight` tree rather than introducing another privileged host root. It exists specifically so the investigated golden build is not the first test of changed infrastructure.

## JIT runner lifecycle

GitHub's organization-scoped JIT API returns `encoded_jit_config`; it is generated per VM and never baked into the golden image. The golden guest contains runner software but no persistent GitHub credential and no SupraLINUX build-source checkout.

Before creating a JIT runner, `scripts/run-kvm-jit-gate.sh` performs additional attribution/serialization checks:

- the golden qcow2 must have a provenance file whose recorded SHA-256 matches the actual file;
- provenance must confirm the temporary build checkout was removed;
- one host-local `flock` serializes all authoritative gates on that host;
- the script refuses to start while another authoritative runner-contract/package-proof workflow is queued or active;
- it snapshots existing workflow-run IDs for the requested workflow and exact PR head SHA before adding the trigger label;
- after the runner becomes busy, exactly one new run for that workflow/head SHA must appear;
- that run ID is bound and queried directly until completion;
- more than one candidate is treated as ambiguous and fails rather than attributing evidence heuristically;
- qemu-guest-agent `guest-exec-status` is checked while waiting, so a runner process that exits before becoming usable fails promptly.

The guest runner is launched explicitly as the non-root runner user with a login shell. The JIT configuration exists only in guest tmpfs under a private runner-owned `/run/supralinux-jit/` directory. The runner deletes the secret config file before `run.sh` begins its job loop. It intentionally leaves the now-empty private directory in the disposable overlay: removing that directory as the non-root runner would require write permission on root-owned `/run`. A file placed directly under root-owned `/run` is invalid for the same reason.

JIT runner creation is non-idempotent. The host therefore performs exactly one organization-scoped `generate-jitconfig` POST per gate. If transport or HTTP status is ambiguous, it does not retry blindly: it queries organization runners for the exact unique VM/runner name, records non-secret reconciliation evidence, deletes any side-effect runner, and classifies the mechanism as infrastructure-invalid.

After two consecutive JIT-mechanism `INFRA_INVALID` incidents, full gate retries are frozen. Recovery requires:

```bash
scripts/check-jit-runner-api-lifecycle.sh
```

The synthetic API preflight verifies the organization runner-group/repository binding, performs one JIT creation, confirms that both runner ID and encoded configuration were returned, deletes the runner, verifies cleanup and never starts a VM or workflow.

A separate startup preflight exercises the exact disposable KVM/golden/JIT injection/non-root runner startup path without adding a PR label or creating a workflow:

```bash
scripts/check-jit-runner-startup-lifecycle.sh
```

It validates the exact byte count returned by QEMU `guest-file-write`, flushes the config file, waits for the JIT runner to reach `online` while still idle, deletes the synthetic runner and verifies cleanup. A startup failure is infrastructure-invalid and does not consume a package Attempt. If the infrastructure reaches the required milestone (`online`, explicit `busy=false`, GitHub session created and `Listening for Jobs`) but a later validator defect makes the validation run exit nonzero, the validation run remains `INFRA_INVALID` while the infrastructure result may be adjudicated `PASS` from immutable hashed evidence; the two outcomes are recorded separately. The same separation applies inside the real runner-contract workflow: failures in post-check evidence capture or validators are infrastructure/validation incidents, not runner or package FAIL, when the underlying runner/KVM contract steps already passed. Host cleanup forces `LC_ALL=C` for libvirt domain-state checks so diagnostic extraction is not fooled by a non-English operator locale.

With a sealed golden image and runner group configured:

```bash
export SUPRALINUX_GITHUB_TOKEN='...'
export SUPRALINUX_RUNNER_GROUP_ID='...'
export SUPRALINUX_GOLDEN_IMAGE='/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2'

scripts/run-kvm-jit-gate.sh runner-contract
scripts/run-kvm-jit-gate.sh authoritative-package-proof
scripts/run-kvm-jit-gate.sh frameworks-sample-proof
```

For each invocation the host creates a fresh overlay VM, obtains/injects a fresh JIT config, waits for the runner to become online, applies exactly one controlled Draft-PR label, binds the resulting workflow run, observes one job, exports diagnostics/evidence and destroys writable state. Fork PRs are rejected by both host and workflow conditions.

Controlled labels:

```text
ci:runner-contract
ci:authoritative-package-proof
ci:frameworks-sample-proof
```

## Authoritative package path

Inside the JIT runner guest:

```text
Ubuntu 26.04 KVM runner VM
├── fresh sbuild/unshare -> .deb + .changes + .buildinfo
└── autopkgtest/QEMU
    └── nested Ubuntu 26.04 KVM test VM
```

Nested KVM is mandatory for the authoritative system-test gate.

## Evidence

Host-side evidence includes host provisioning/preflight data, verified source-image provenance, exact source commit, golden build inputs, guest provisioning/seal evidence, nested test-image SHA-256, offline sysprep log, qcow2 validation, final golden-image SHA-256, workflow baseline IDs, bound workflow run ID, PR head SHA, VM definition, runner state snapshots and exported diagnostics.

Repository Policy additionally executes `bash -n scripts/*.sh` so shell syntax is continuously validated on GitHub-hosted Ubuntu 26.04 before these scripts reach real infrastructure.

The authoritative workflow separately uploads runner/package evidence. Promotion decisions require the bound workflow result plus retained evidence.

## Current certification state

The authoritative Ubuntu 26.04 host and sealed golden image are **PASS**. The real `runner-contract` is also **PASS**: the disposable JIT runner proved Actions Runner provenance, Ubuntu 26.04/KVM boundaries, required build/test tools, nested KVM, evidence capture, repository invariants, artifact upload and host-side cleanup/export. Historical JIT API, guest-startup and evidence-capture `INFRA_INVALID` incidents remain preserved as closed evidence and do not alter the current PASS.

The current live gate is `authoritative-package-proof`, back to **pending** with one retry authorized after closing a repeated-infrastructure freeze. Two consecutive synthetic certification runs had reached valid `sbuild/unshare` execution and finished the package build successfully, then failed before the autopkgtest testbed could boot. Those executions remain preserved as `INFRA_INVALID` historical evidence; they consume synthetic package execution attempts but do not create a canonical KDE package FAIL and do not alter KDE package state.

The repeated-failure diagnosis identified a gap in the first remediation. On autopkgtest 5.55, KVM-capable x86_64 QEMU invocations include `-enable-kvm`. The first fake-QEMU test covered `-accel` and `-machine accel=...` but did not reproduce that provider argument. The corrected wrapper now removes provider/top-level acceleration selectors and emits exactly one canonical KVM selector: `-machine accel=kvm` when a machine option exists, otherwise `-accel kvm`.

Recovery was certified by Repository Policy run `36819196488`: ShellCheck passed, the QEMU-wrapper functional test passed, `scripts/check-autopkgtest-qemu-argv-lifecycle.sh` inspected autopkgtest 5.55 and confirmed `provider_contract=-enable-kvm`, normalized the synthetic provider argv to `-accel kvm`, and passed; repository invariants and the authoritative-KVM live-state validator also passed. That evidence closes the repeated-infrastructure freeze and authorizes one new package-proof execution.

Plasma, KWin and session work remain locked until `authoritative-package-proof` and the subsequent `frameworks-sample-proof` pass.


## Frameworks sample gate

After runner-contract and the synthetic authoritative package proof pass, a third fresh JIT guest runs `frameworks-sample-proof`. It rebuilds canonical KArchive 6.30.0 with the exact retained ECM 6.30.0 predecessor and records package/test/ABI/consumer evidence. This is the required Frameworks lane certification checkpoint before KWin, Plasma or session work.


## Full certification entrypoint

For an admitted host, use the single fail-closed entrypoint rather than manually sequencing gates:

```bash
SUPRALINUX_GITHUB_TOKEN=... \
SUPRALINUX_RUNNER_GROUP_ID=... \
scripts/run-authoritative-kvm-certification.sh
```

The local checkout and PR head must be identical. The golden image may originate from an earlier commit only when its versioned golden-input fingerprint exactly matches the PR HEAD being certified; otherwise execution fails before a JIT runner is created and the image must be rebuilt. `source_commit` remains historical provenance, not a mutable live-state lock. Golden replacement is opt-in through `SUPRALINUX_REBUILD_GOLDEN=1`; evidence is retained outside the repository and is never auto-committed.
