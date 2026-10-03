#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/manifests/kde-tier2-kmime-legacy-provider.json"
WORK="$ROOT/.work/kde-tier2-kmime-legacy-provider-materialization"
EVIDENCE="$ROOT/evidence/kde-tier2-kmime-legacy-provider-materialization"
UBUNTU_LIST="$WORK/ubuntu.sources.list"
UBUNTU_LISTS="$WORK/apt-lists-ubuntu"
REFERENCE="$WORK/reference"
SOURCE_PARENT="$WORK/source"
STATE=FAIL
STAGE=initialization

rm -rf "$WORK" "$EVIDENCE"
mkdir -p "$REFERENCE" "$SOURCE_PARENT" "$EVIDENCE"
exec > >(tee "$EVIDENCE/pipeline.log") 2>&1

write_result(){
  local rc=$?
  python3 - "$EVIDENCE/result.json" "$STATE" "$rc" "$STAGE" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
d={}
if p.exists():
    try:
        d=json.loads(p.read_text())
    except Exception:
        d={}
d.update({
    "result":sys.argv[2],
    "exit_code":int(sys.argv[3]),
    "stage":sys.argv[4],
    "package_attempted":False,
    "package_state_effect":"none",
})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends dpkg-dev ubuntu-keyring xz-utils

cat > "$UBUNTU_LIST" <<'EOF'
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe
EOF

sudo mkdir -p "$UBUNTU_LISTS"
sudo chown _apt:root "$UBUNTU_LISTS"
ubuntu_apt=(-o "Dir::Etc::sourcelist=$UBUNTU_LIST" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=$UBUNTU_LISTS" -o "APT::Get::List-Cleanup=0")
sudo apt-get "${ubuntu_apt[@]}" update

readarray -t cfg < <(python3 - "$MANIFEST" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
r=m["source_reference"]
s=m["supralinux_package"]
a=m["adaptation"]
for value in (
    r["source_package"],
    r["ubuntu_version"],
    r["dsc_sha256"],
    r["debian_tar_sha256"],
    r["orig_tar_sha256"],
    s["package_version"],
    a["old_dependency"],
    a["new_dependency"],
):
    print(value)
PY
)

SOURCE_PACKAGE="${cfg[0]}"
UBUNTU_VERSION="${cfg[1]}"
DSC_SHA="${cfg[2]}"
DEBIAN_SHA="${cfg[3]}"
ORIG_SHA="${cfg[4]}"
PACKAGE_VERSION="${cfg[5]}"
OLD_DEP="${cfg[6]}"
NEW_DEP="${cfg[7]}"

STAGE=source-download
pushd "$REFERENCE" >/dev/null
apt-get "${ubuntu_apt[@]}" source --download-only "$SOURCE_PACKAGE=$UBUNTU_VERSION"
popd >/dev/null

DSC="$(find "$REFERENCE" -maxdepth 1 -type f -name '*.dsc' -print -quit)"
DEBIAN_TAR="$(find "$REFERENCE" -maxdepth 1 -type f -name '*.debian.tar.*' -print -quit)"
ORIG="$(find "$REFERENCE" -maxdepth 1 -type f -name '*.orig.tar.*' ! -name '*.asc' -print -quit)"
[[ -n "$DSC" && -n "$DEBIAN_TAR" && -n "$ORIG" ]]

[[ "$(sha256sum "$DSC" | awk '{print $1}')" == "$DSC_SHA" ]]
[[ "$(sha256sum "$DEBIAN_TAR" | awk '{print $1}')" == "$DEBIAN_SHA" ]]
[[ "$(sha256sum "$ORIG" | awk '{print $1}')" == "$ORIG_SHA" ]]

STAGE=source-extract
SRC="$SOURCE_PARENT/kmime-25.12.3"
dpkg-source -x "$DSC" "$SRC"
cp -a "$ORIG" "$SOURCE_PARENT/$(basename "$ORIG")"

STAGE=packaging-adaptation
python3 - "$SRC/debian/control" "$SRC/debian/changelog" "$OLD_DEP" "$NEW_DEP" "$PACKAGE_VERSION" <<'PY'
import re,sys
from pathlib import Path

control=Path(sys.argv[1])
changelog=Path(sys.argv[2])
old=sys.argv[3]
new=sys.argv[4]
version=sys.argv[5]

text=control.read_text()
paragraphs=text.split("\n\n")
source_found=False
runtime_found=False
output=[]

for paragraph in paragraphs:
    if re.search(r"(?m)^Source:\s*kmime\s*$",paragraph):
        source_found=True
        paragraph=re.sub(
            r"(?m)^Maintainer:.*$",
            "Maintainer: SupraLINUX Build System <build@supralinux.invalid>",
            paragraph,
            count=1,
        )
    if re.search(r"(?m)^Package:\s*libkpim6mime6\s*$",paragraph):
        runtime_found=True
        if paragraph.count(old)!=1:
            raise SystemExit(f"runtime dependency baseline drift: expected one {old!r}")
        paragraph=paragraph.replace(old,new)
    output.append(paragraph)

if not source_found:
    raise SystemExit("Source stanza not found")
if not runtime_found:
    raise SystemExit("libkpim6mime6 stanza not found")

control.write_text("\n\n".join(output))

entry=f"""kmime ({version}) resolute; urgency=medium

  * SupraLINUX compatibility provider: allow the authoritative
    libkf6mime-data package as an alternative data provider for
    the real libKPim6Mime.so.6 legacy runtime.

 -- SupraLINUX Build System <build@supralinux.invalid>  Tue, 22 Sep 2026 00:00:00 +0000

"""
changelog.write_text(entry+changelog.read_text())
PY

python3 - "$SRC/debian/control" "$OLD_DEP" "$NEW_DEP" <<'PY'
import re,sys
text=open(sys.argv[1]).read()
runtime=next(
    (p for p in text.split("\n\n") if re.search(r"(?m)^Package:\s*libkpim6mime6\s*$",p)),
    None,
)
if runtime is None:
    raise SystemExit("runtime stanza missing after adaptation")
if sys.argv[2] in runtime:
    raise SystemExit("old dependency remains after adaptation")
if sys.argv[3] not in runtime:
    raise SystemExit("new dependency missing after adaptation")
print("legacy runtime dependency adaptation: PASS")
PY

STAGE=source-package-build
pushd "$SOURCE_PARENT" >/dev/null
dpkg-source -b "$SRC"
popd >/dev/null

NEW_DSC="$(find "$SOURCE_PARENT" -maxdepth 1 -type f -name "kmime_${PACKAGE_VERSION}.dsc" -print -quit)"
NEW_DEBIAN="$(find "$SOURCE_PARENT" -maxdepth 1 -type f -name "kmime_${PACKAGE_VERSION}.debian.tar.*" -print -quit)"
[[ -n "$NEW_DSC" && -n "$NEW_DEBIAN" ]]

cp -a "$NEW_DSC" "$NEW_DEBIAN" "$SOURCE_PARENT/$(basename "$ORIG")" "$EVIDENCE/"

STAGE=evidence
python3 - "$MANIFEST" "$EVIDENCE" "$NEW_DSC" "$NEW_DEBIAN" "$SOURCE_PARENT/$(basename "$ORIG")" <<'PY'
import hashlib,json,sys
from pathlib import Path

manifest=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])
dsc=Path(sys.argv[3])
debian_tar=Path(sys.argv[4])
orig=Path(sys.argv[5])

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

version=manifest["supralinux_package"]["package_version"]
if f"Version: {version}" not in dsc.read_text():
    raise SystemExit("materialized dsc version mismatch")

result={
    "result":"PASS",
    "package_attempted":False,
    "package_state_effect":"none",
    "source_package":"kmime",
    "package_version":version,
    "dsc_sha256":sha(dsc),
    "debian_tar_sha256":sha(debian_tar),
    "orig_tar_sha256":sha(orig),
    "source_reference":manifest["source_reference"],
    "adaptation":manifest["adaptation"],
}
(out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
(out/"artifact-sha256.txt").write_text(
    f"{result['dsc_sha256']}  {dsc.name}\n"
    f"{result['debian_tar_sha256']}  {debian_tar.name}\n"
    f"{result['orig_tar_sha256']}  {orig.name}\n"
)
print(json.dumps(result,indent=2))
PY

STATE=PASS
STAGE=complete
echo "KMime legacy compatibility-provider materialization: PASS"
