# Retained Frameworks support inputs

`manifests/frameworks-support-inputs.json` records separately retained support
packages required by new consumers. The original 65-node Frameworks DAG, artifact
plan and milestone payload remain immutable. The effective input resolver adds
these providers only after validating their original source, version, binary
identities, workflow job, artifact digest and closed result.

KDocTools 6.30.0-0supralinux1 retains its original hosted clean-package preflight
PASS (run 35700002095, job 106656022342). Its complete original archive includes
four main binaries, two debug binaries, sources, buildinfo, changes and logs.
All archive members are hashed; source and changes checksum closures and binary
identities were inspected, and restoration into an empty cache was verified.
Review evidence is small; full unmodified logs remain in the retained archive.
This restores an eligible build input without claiming new authoritative package
certification. The final rebuild still has to certify this provider on KVM.

The materializer verifies the complete original archive before extracting only
the explicitly reviewed binaries. Cache admission still checks the entire old
milestone pool, then admits separately restored inputs by source, version,
architecture, digest and evidence link. It does not alter the milestone. Changes
to this transport or provider selection require a fresh input preflight before a
candidate package Attempt. The preflight freezes the registry, verifier and
selected provider proof hashes as well as the ordinary execution inputs.

Ksshaskpass uses the matched provider to generate its upstream manual. It keeps
Ubuntu Qt and QtKeychain, the Ubuntu epoch and the ssh-askpass alternative with
its manual slave. The reviewed fixture drives actual public Qt dialog widgets,
then runs the original event loops and application result handling. Its five
cases cover masked entry, cancellation, confirmation and information prompts.
HOME/XDG directories, D-Bus and offscreen windows are private; test data is
synthetic. An unchanged Ubuntu-built fixture and a rebuilt consumer must pass
after candidate upgrade. Real wallet, OpenSSH and Wayland session behavior remain
desktop integration gates.

Kwrited 4:6.7.5-0supralinux1 closed authoritative Attempt 1 PASS on source
3fc75d2186c2236e5a10d27a8ba375fd4fb5ec65, run 37346882178/job 111887559718.
The clean build, lintian, actual KDED module loading, PTY text normalization,
private notification delivery, PTY cleanup, Ubuntu client after upgrade and
rebuilt consumer passed. Its original archive SHA-256 is
bf9747eec1772b04f8cc49a3be0ede217a43ba14369a41161ce86404f9d7ed72.
The retained source, binary/debug package, buildinfo, changes and test logs restore
offline. Full session integration remains a separate gate.
