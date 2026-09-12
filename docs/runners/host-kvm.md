# KVM/libvirt host orchestration

Status: **host bootstrap, golden-image build and JIT orchestration implemented; not yet executed on a real host**  
Last reviewed: **2026-09-11**

The long-lived host is an infrastructure provider only. It is not a SupraLINUX build runner and must not be treated as release evidence. Its job is to provide KVM/libvirt, build the sealed Ubuntu 26.04 golden runner image, create one disposable runner guest per authoritative GitHub Actions job, preserve evidence, and destroy writable VM state afterwards.

## Host bootstrap and preflight

The supported host recipe currently targets Ubuntu 26.04 amd64/x86_64:

```bash
scripts/provision-kvm-host.sh
# open a new login session
scripts/check-kvm-host.sh
```

The bootstrap installs KVM/QEMU, libvirt, `virt-install`, libguestfs and support tools; configures `kvm`/`libvirt` access; prepares `/var/lib/supralinux` state directories; and starts the selected libvirt network when available.

It does **not** alter firmware/BIOS settings or forcibly reload KVM modules. The read-only preflight requires visible CPU virtualization, usable `/dev/kvm`, nested KVM, required groups/tools (including libguestfs and `flock`), working `qemu:///system` and an active libvirt network.

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

Default output:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

Existing golden images are not replaced unless `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1` is explicitly supplied. Failed builds preserve diagnostic state and do not publish a replacement image.

## JIT runner lifecycle

GitHub's repository JIT API returns `encoded_jit_config`; it is generated per VM and never baked into the golden image. The golden guest contains runner software but no persistent GitHub credential and no SupraLINUX build-source checkout.

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

The guest runner is launched explicitly as the non-root runner user with a login shell. The JIT configuration exists only in guest `/run`, is read immediately before runner startup and is deleted before the runner begins its job loop.

With a sealed golden image and runner group configured:

```bash
export SUPRALINUX_GITHUB_TOKEN='...'
export SUPRALINUX_RUNNER_GROUP_ID='...'
export SUPRALINUX_GOLDEN_IMAGE='/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2'

scripts/run-kvm-jit-gate.sh runner-contract
scripts/run-kvm-jit-gate.sh authoritative-package-proof
```

For each invocation the host creates a fresh overlay VM, obtains/injects a fresh JIT config, waits for the runner to become online, applies exactly one controlled Draft-PR label, binds the resulting workflow run, observes one job, exports diagnostics/evidence and destroys writable state. Fork PRs are rejected by both host and workflow conditions.

Controlled labels:

```text
ci:runner-contract
ci:authoritative-package-proof
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

## Current blocker

No real KVM host has executed this complete chain yet. Therefore host preflight, source-image fetch/hash, golden-image build/hash, nested KVM, JIT startup, runner-group policy, QEMU system testing and cleanup/export behavior remain **pending execution**, not PASS.
