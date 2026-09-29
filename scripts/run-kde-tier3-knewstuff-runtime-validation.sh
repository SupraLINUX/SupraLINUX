#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-knewstuff-runtime-validation.json"
L0="${ROOT}/manifests/kde-tier3-build-level0.json"; L2="${ROOT}/manifests/kde-tier3-build-level2.json"
WORK="${ROOT}/.work/knewstuff-runtime-validation"; INPUTS="${WORK}/inputs"; REPO="${WORK}/repo"; ROOTFS="${WORK}/rootfs"
EV="${ROOT}/evidence/kde-tier3-knewstuff-runtime-validation"; RESULT="${EV}/result.json"
STATE=INFRA_INVALID; STAGE=initialization; STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"
rm -rf "${WORK}" "${EV}"; mkdir -p "${INPUTS}" "${REPO}" "${EV}"
exec > >(tee "${EV}/pipeline.log") 2>&1
finish(){ rc=$?; finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; python3 - "${RESULT}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d={}
if p.exists():
 try:d=json.loads(p.read_text())
 except Exception:d={}
d.update({"schema":1,"node":"knewstuff","validation_result":sys.argv[2],"result":sys.argv[2],"exit_code":int(sys.argv[3]),"stage":sys.argv[4],"package_attempted":False,"consumes_package_attempt":False,"validation_run_kind":"runtime-only","started_at":sys.argv[5],"finished_at":sys.argv[6]})
p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
PY
}; trap finish EXIT
python3 - "${MANIFEST}" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r.get("state")=="execution-authorized" and r.get("execution_authorized") is True
assert r.get("package_attempted") is False and r.get("consumes_package_attempt") is False
PY
download(){ id="$1"; sha="$2"; dest="$3"; mkdir -p "${dest}"; zip="${dest}.zip"; curl --fail --silent --show-error --location --retry 3 --retry-delay 2 -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"; printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check -; unzip -q "${zip}" -d "${dest}"; }
STAGE=artifact-plan
python3 - "${MANIFEST}" "${L0}" "${L2}" "${EV}/artifact-plan.tsv" <<'PY'
import json,sys
rv,l0,l2=[json.load(open(x)) for x in sys.argv[1:4]]; out=sys.argv[4]; rows={}
def add(i,sha,label):
 if i in rows and rows[i][0]!=sha: raise SystemExit(f"artifact {i} digest conflict")
 rows[i]=(sha,label)
s=rv["subject"]["retained_build_evidence"]; add(s["artifact_id"],s["artifact_sha256"],"knewstuff")
p=rv["runtime_provider"]["pass_evidence"]; add(p["artifact_id"],p["artifact_sha256"],"kcmutils")
for camp,node in ((l0,l0["nodes"]["knewstuff"]),(l2,l2["nodes"]["kcmutils"])):
 for x in sorted(set(node.get("retained_input_ids",[]))|set(node.get("support_input_ids",[]))|set(node.get("external_runtime_inputs",[]))):
  q=camp.get("retained_predecessors",{}).get(x) or camp.get("support_predecessors",{}).get(x)
  if not q: raise SystemExit(f"missing retained provider spec: {x}")
  add(q["artifact_id"],q["artifact_sha256"],x)
with open(out,"w") as f:
 for i,(sha,label) in sorted(rows.items()): f.write(f"{i}\t{sha}\t{label}\n")
PY
while IFS=$'\t' read -r id sha label; do download "${id}" "${sha}" "${INPUTS}/${id}-${label}"; done < "${EV}/artifact-plan.tsv"
STAGE=artifact-contract
python3 - "${MANIFEST}" "${L0}" "${L2}" "${INPUTS}" "${REPO}" "${EV}" <<'PY'
import json,shutil,subprocess,sys
from pathlib import Path
rv,l0,l2=json.load(open(sys.argv[1])),json.load(open(sys.argv[2])),json.load(open(sys.argv[3])); root,repo,ev=map(Path,sys.argv[4:7]); specs=[]
def add(label,aid,ver,expected): specs.append((label,aid,ver,set(expected)))
s=rv["subject"]; add("knewstuff",s["retained_build_evidence"]["artifact_id"],s["package_version"],s["expected_binary_packages"])
p=rv["runtime_provider"]; add("kcmutils",p["pass_evidence"]["artifact_id"],p["package_version"],p["expected_binary_packages"])
for camp,node in ((l0,l0["nodes"]["knewstuff"]),(l2,l2["nodes"]["kcmutils"])):
 for x in sorted(set(node.get("retained_input_ids",[]))|set(node.get("support_input_ids",[]))|set(node.get("external_runtime_inputs",[]))):
  q=camp.get("retained_predecessors",{}).get(x) or camp.get("support_predecessors",{}).get(x); add(x,q["artifact_id"],q["version"],q["expected_binary_packages"])
seen={}
for label,aid,ver,expected in specs:
 artifact_dir=root/f"{aid}-{label}"
 if not artifact_dir.is_dir(): raise SystemExit(f"{label}: extracted artifact directory missing: {artifact_dir}")
 actual={}
 for deb in artifact_dir.rglob("*.deb"):
  pkg=subprocess.check_output(["dpkg-deb","-f",str(deb),"Package"],text=True).strip(); vv=subprocess.check_output(["dpkg-deb","-f",str(deb),"Version"],text=True).strip()
  if vv!=ver: raise SystemExit(f"{label}/{pkg}: version {vv} != {ver}")
  actual[pkg]=deb
 if set(actual)!=expected: raise SystemExit(f"{label}: binary set mismatch")
 for pkg,deb in actual.items():
  if pkg in seen and seen[pkg][0]!=ver: raise SystemExit(f"{pkg}: conflicting retained versions")
  seen[pkg]=(ver,label); dst=repo/deb.name
  if not dst.exists(): shutil.copy2(deb,dst)
(ev/"retained-package-owners.json").write_text(json.dumps({k:{"version":z[0],"provider":z[1]} for k,z in sorted(seen.items())},indent=2)+"\n")
PY
STAGE=rootfs-bootstrap
sudo apt-get update; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mmdebstrap dpkg-dev unzip curl
sudo mmdebstrap --variant=minbase --architectures=amd64 --components=main,universe resolute "${ROOTFS}" http://azure.archive.ubuntu.com/ubuntu
(cd "${REPO}" && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz)
sudo mkdir -p "${ROOTFS}/tmp/supralinux"; sudo cp -a "${REPO}/." "${ROOTFS}/tmp/supralinux/"
echo 'deb [trusted=yes] file:/tmp/supralinux ./' | sudo tee "${ROOTFS}/etc/apt/sources.list.d/supralinux.list" >/dev/null
sudo chroot "${ROOTFS}" apt-get update |& tee "${EV}/rootfs-apt-update.log"
STATE=FAIL; STAGE=runtime-install
mapfile -t runtime_pkgs < <(python3 - "${MANIFEST}" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
for x in r["subject"]["runtime_install_packages"]+r["runtime_provider"]["runtime_install_packages"]: print(x)
PY
)
sudo chroot "${ROOTFS}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends binutils g++ pkg-config qt6-declarative-dev "${runtime_pkgs[@]}" |& tee "${EV}/runtime-install.log"
sudo chroot "${ROOTFS}" apt-get check |& tee "${EV}/apt-check.log"
STAGE=version-proof
python3 - "${MANIFEST}" "${ROOTFS}" "${EV}/version-proof.json" <<'PY'
import json,subprocess,sys
from pathlib import Path
r=json.load(open(sys.argv[1])); root=sys.argv[2]; rows={}
for key in ("subject","runtime_provider"):
 sec=r[key]; want=sec["package_version"]
 for pkg in sec["runtime_install_packages"]:
  got=subprocess.check_output(["sudo","chroot",root,"dpkg-query","-W","-f=$"+"{Version}",pkg],text=True).strip()
  if got!=want: raise SystemExit(f"{pkg}: installed {got} != {want}")
  rows[pkg]=got
allq=subprocess.run(["sudo","chroot",root,"dpkg-query","-W","-f=$"+"{Package}\t$"+"{Version}\n"],text=True,capture_output=True,check=True).stdout
if any("kcmutils" in x.lower() and "6.24.0-0ubuntu1" in x for x in allq.splitlines()): raise SystemExit("Ubuntu KCMUtils 6.24 fallback remains installed")
Path(sys.argv[3]).write_text(json.dumps(rows,indent=2,sort_keys=True)+"\n")
PY
STAGE=elf-resolution
sudo chroot "${ROOTFS}" bash -ceu 'for pkg in knewstuff-dialog6 libkf6newstuffcore6 libkf6newstuffwidgets6 libkf6kcmutils-bin libkf6kcmutils6 libkf6kcmutilscore6 libkf6kcmutilsquick6; do dpkg -L "$pkg"; done | sort -u | while read -r p; do [ -f "$p" ] || continue; if readelf -h "$p" >/dev/null 2>&1; then ldd "$p" 2>/dev/null || true; fi; done' | tee "${EV}/ldd.log"
if grep -Fq 'not found' "${EV}/ldd.log"; then
  echo 'unresolved runtime shared-object dependency detected' >&2
  exit 1
fi
STAGE=qml-smoke
cat > "${WORK}/qml-smoke.cpp" <<'CPP'
#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QUrl>
#include <cstdio>
int main(int argc,char**argv){QGuiApplication app(argc,argv);QQmlEngine e;const char* s[]={"import QtQuick\nimport org.kde.newstuff\nItem {}","import QtQuick\nimport org.kde.kcmutils\nItem {}"};for(auto x:s){QQmlComponent c(&e);c.setData(x,QUrl("file:///smoke.qml"));if(c.isError()){for(auto &z:c.errors())fprintf(stderr,"%s\n",qPrintable(z.toString()));return 2;}}for(int i=1;i<argc;i++){QQmlComponent c(&e,QUrl::fromLocalFile(argv[i]));if(c.isError()){for(auto &z:c.errors())fprintf(stderr,"%s\n",qPrintable(z.toString()));return 3;}}return 0;}
CPP
sudo cp "${WORK}/qml-smoke.cpp" "${ROOTFS}/tmp/qml-smoke.cpp"
sudo chroot "${ROOTFS}" bash -ceu 'g++ /tmp/qml-smoke.cpp -o /tmp/qml-smoke $(pkg-config --cflags --libs Qt6Gui Qt6Qml)'
qmlbase=/usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/newstuff
sudo chroot "${ROOTFS}" unshare --net env QT_QPA_PLATFORM=offscreen /tmp/qml-smoke "${qmlbase}/EntryDetails.qml" "${qmlbase}/Page.qml" |& tee "${EV}/qml-smoke.log"
STAGE=complete; STATE=PASS
