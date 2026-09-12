# Authoritative KVM runner provisioning

Status: **repository implementation complete for current Phase 1 design; real KVM certification pending**  
Last reviewed: **2026-09-11**

The long-lived KVM/libvirt host is an infrastructure provider, not the build runner. The authoritative identity begins inside each disposable Ubuntu 26.04 JIT runner VM.

## Host boundary

Host bootstrap/preflight:

```text
scripts/provision-kvm-host.sh
scripts/check-kvm-host.sh
```

The supported recipe targets Ubuntu 26.04 amd64/x86_64, installs the declared KVM/libvirt/libguestfs toolchain, prepares state/evidence directories and group access, and validates nested KVM/readable-writable `/dev/kvm`, `qemu:///system`, required tools and active libvirt networking. It does not silently modify BIOS/firmware or forcibly reload KVM modules.

## Released Ubuntu source image

`scripts/fetch-ubuntu-26.04-cloud-image.sh` fetches the released Resolute amd64 cloud image into stable host storage:

```text
/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img
```

The same directory retains `SHA256SUMS`, `SHA256SUMS.gpg` and provenance. At fetch time the script verifies Ubuntu's detached signature with the cloud-image keyring and verifies the selected image SHA-256.

## Mandatory use-time re-verification

A previously verified local file is not trusted merely because its provenance file still exists. Before the golden builder inspects or uses the image, `scripts/verify-ubuntu-cloud-image-provenance.sh` revalidates it from the retained signed Ubuntu metadata.

The verifier requires:

- exact image filename `ubuntu-26.04-server-cloudimg-amd64.img`;
- `release=resolute` and `architecture=amd64` provenance;
- readable `SHA256SUMS`, `SHA256SUMS.gpg` and configured Ubuntu cloud-image keyring;
- successful `gpgv` verification of `SHA256SUMS.gpg` over `SHA256SUMS`;
- exactly one signed checksum entry for the expected image filename;
- provenance SHA-256 equal to that signed value;
- current image bytes whose SHA-256 equals the same signed value.

The builder retains the verifier output as `source-image-verification.txt`. This protects against local mutation between download and use, including mutation of image and provenance together without a valid Ubuntu signature.

Repository Policy executes a real functional signature test with an ephemeral GPG key. It accepts a correctly signed fixture and rejects tampered image bytes, modified signed metadata, invalid provenance markers, duplicate provenance hashes and jointly modified image/provenance that do not match signed metadata.

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
6. provisions the Ubuntu 26.04 build/test toolchain and verified GitHub Actions runner;
7. builds the nested Resolute/amd64 `autopkgtest` QEMU image and records its hash;
8. removes runner registration/work state;
9. removes the temporary `/opt/supralinux-src` build checkout and records `source_checkout_removed=yes`;
10. powers the VM off;
11. exports guest evidence;
12. runs explicit offline `virt-sysprep` identity/state cleanup;
13. flattens the overlay and runs `qemu-img check`;
14. writes final golden-image SHA-256/provenance including `source_image_provenance_verified=yes`.

Default output:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

Replacement requires explicit `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1`. Failed builds keep diagnostic state and do not publish a replacement golden image.

## Guest components

`scripts/provision-authoritative-runner-guest.sh` validates Ubuntu 26.04/KVM, installs declared build/test tools, subordinate IDs and KVM access, enables qemu-guest-agent, installs the GitHub runner after checking GitHub-published SHA-256, and records provenance.

`scripts/prepare-autopkgtest-qemu-image.sh` requires usable nested KVM and builds:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

with real image SHA-256/provenance.

`scripts/seal-authoritative-runner-image.sh` pre-seals runner/package state inside the guest. Clone identity is deliberately reset after shutdown by the host-side offline `virt-sysprep` stage.

## Runtime JIT lifecycle

The golden image contains runner software but no persistent GitHub registration token/PAT/JIT config and no temporary SupraLINUX source checkout.

`scripts/run-kvm-jit-gate.sh` creates a fresh overlay VM, validates golden provenance, requests repository `generate-jitconfig`, injects the encoded JIT config into guest `/run`, launches the runner non-root, waits until it is online, applies one controlled PR label, binds one new workflow run for the exact PR head SHA, exports diagnostics/evidence and destroys writable state.

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
```

Both host and workflows refuse fork PRs.

## Certification sequence

A golden image remains **pending** until real evidence establishes:

1. host preflight PASS;
2. signed Ubuntu source-image fetch verification and real source SHA-256;
3. use-time GPG signature/SHA-256 re-verification PASS;
4. golden build from an exact source commit;
5. temporary source checkout absent from the golden image;
6. offline sysprep/flatten/qcow2-check evidence and final golden SHA-256;
7. nested `autopkgtest` image SHA-256;
8. `runner-contract.yml` PASS on a disposable JIT KVM guest, including real nested-KVM probe;
9. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest, including clean `sbuild` and KVM-only `autopkgtest/QEMU`;
10. retained workflow artifacts plus host/runner diagnostics.

Until those real VMs execute, no authoritative PASS or image hash is claimed.
