# First desktop test image

The first user-testable SupraLINUX image must contain the selected desktop,
boot a real session and install onto a disposable disk before delivery. No
SupraLINUX live ISO or verified installer is currently available.

`manifests/desktop-image-profile.json` defines a preliminary core dependency
analysis for the compositor/session, settings, lock screen, audio, network,
portal and Discover. It is not the final installation seed. Other upstream
components remain in the build inventory; this analysis does not exclude them
or define exceptions to the final desktop profile.

Generate a current plan without creating a VM or changing the host:

```sh
python3 scripts/plan-desktop-image.py \
  --profile manifests/desktop-image-profile.json \
  --output .work/desktop-image-plan.json
```

The planner follows the canonical Plasma DAG and rejects unknown nodes or
dependency cycles. A recorded package PASS requires the exact result digest,
source commit, source/version identity, authoritative build, lintian and
installed-test results, and declared complete offline artifact retention.
Unreviewed packages and compatibility holds remain pending.

Recorded package evidence does not restore or certify the image payload. The
composition gate must restore sources/binaries from retained artifacts and
verify their hashes, source package, Debian version and architecture before use.
Even a complete package plan cannot authorize an image build by itself.

After the package dependencies close, the image needs minimal Ubuntu composition,
an exact package seed, signed APT metadata, live/installer generation and
Btrfs/Snapper recovery integration. Its boot, installation, first start, updates
and recovery must be exercised on owned disposable KVM disks. Tests use the
certified isolated QEMU SLIRP transport or zero NIC, preserving the host's network
configuration and removing every ephemeral VM and overlay after the gate.

The final release additionally requires the complete desktop profile,
Ubuntu/Qt/application compatibility, selected Gear packages, hardware QA and a
clean-input rebuild/restore campaign. Final merge and stable publication remain
separate approved gates.
