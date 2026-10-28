#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="/var/lib/supralinux/proposed-integration-payload"
EVIDENCE="${ROOT}/evidence/authoritative-supralinux-proposed-integration"
KEYRING="/usr/share/keyrings/supralinux-integration-certification.gpg"
FRAMEWORKS_SUITE="resolute-supralinux-frameworks"
PROPOSED_SUITE="resolute-supralinux-proposed"
rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}"
for command_name in apt-cache apt-get dpkg-query gpgv python3 sha256sum; do
  command -v "${command_name}" >/dev/null 2>&1 || { printf 'Missing integration command: %s\n' "${command_name}" >&2; exit 1; }
done
python3 - "${PAYLOAD}" "$(git -C "${ROOT}" rev-parse HEAD)" <<'PY'
import hashlib,json,sys
from pathlib import Path
payload=Path(sys.argv[1]); head=sys.argv[2]; manifest=json.loads((payload/"payload.json").read_text())
if not (manifest.get("state")=="PASS" and manifest.get("kind")=="supralinux-proposed-integration-payload" and manifest.get("source_commit")==head and manifest.get("frameworks_pass_nodes")==65 and manifest.get("proposed_candidate_count")==24 and manifest.get("signature_verification")=="PASS" and manifest.get("ephemeral_signing_key") is True and manifest.get("private_signing_key_retained") is False and manifest.get("repository_active") is False and manifest.get("production_activation_eligible") is False and manifest.get("stable_publication_authorized") is False and manifest.get("package_attempt_consumed") is False and manifest.get("sbuild_invoked") is False):
    raise SystemExit("invalid proposed integration payload contract")
for path in payload.rglob("*"):
    if path.is_symlink(): raise SystemExit(f"integration payload symlink rejected: {path}")
key=payload/"certification-public-key.gpg"
if hashlib.sha256(key.read_bytes()).hexdigest()!=manifest["public_key_sha256"]: raise SystemExit("integration public key digest mismatch")
PY
install -o root -g root -m 0644 "${PAYLOAD}/certification-public-key.gpg" "${KEYRING}"
gpgv --keyring "${KEYRING}" "${PAYLOAD}/repos/frameworks/dists/${FRAMEWORKS_SUITE}/InRelease" |& tee "${EVIDENCE}/frameworks-signature.log"
gpgv --keyring "${KEYRING}" "${PAYLOAD}/repos/proposed/dists/${PROPOSED_SUITE}/InRelease" |& tee "${EVIDENCE}/proposed-signature.log"
cat > /etc/apt/sources.list.d/supralinux-integration.sources <<EOF
Types: deb
URIs: file:${PAYLOAD}/repos/frameworks
Suites: ${FRAMEWORKS_SUITE}
Components: main
Architectures: amd64
Signed-By: ${KEYRING}

Types: deb
URIs: file:${PAYLOAD}/repos/proposed
Suites: ${PROPOSED_SUITE}
Components: main
Architectures: amd64
Signed-By: ${KEYRING}
EOF
cat > /etc/apt/preferences.d/supralinux-integration.pref <<EOF
Package: *
Pin: release n=${FRAMEWORKS_SUITE}
Pin-Priority: 1001

Package: *
Pin: release n=${PROPOSED_SUITE}
Pin-Priority: 1001
EOF
apt-get -o Acquire::Languages=none -o Acquire::AllowInsecureRepositories=false -o APT::Get::AllowUnauthenticated=false update |& tee "${EVIDENCE}/apt-update.log"
mapfile -t SEED < <(python3 - "${PAYLOAD}/install-seed.json" <<'PY'
import json,sys
for item in json.load(open(sys.argv[1]))["packages"]: print(f'{item["package"]}={item["version"]}')
PY
)
if (( ${#SEED[@]} == 0 )); then printf 'Proposed integration install seed is empty.\n' >&2; exit 1; fi
python3 - "${PAYLOAD}/install-seed.json" "${EVIDENCE}/preinstalled.json" <<'PY'
import json,subprocess,sys
seed=json.load(open(sys.argv[1]))["packages"]; present=[]
for item in seed:
    proc=subprocess.run(["dpkg-query","-W","-f=${db:Status-Status}\t${Version}\n",item["package"]],text=True,capture_output=True)
    if proc.returncode==0:
        status,version=proc.stdout.rstrip("\n").split("\t",1)
        if status=="installed": present.append({"package":item["package"],"version":version})
json.dump({"schema":1,"preinstalled":present},open(sys.argv[2],"w"),indent=2,sort_keys=True); open(sys.argv[2],"a").write("\n")
if present: raise SystemExit("clean-install precondition failed: proposed packages already installed")
PY
python3 - "${PAYLOAD}/install-seed.json" "${EVIDENCE}/candidate-policy.json" <<'PY'
import json,subprocess,sys
seed=json.load(open(sys.argv[1]))["packages"]; rows=[]
for item in seed:
    out=subprocess.check_output(["apt-cache","policy",item["package"]],text=True); candidate=""
    for line in out.splitlines():
        if line.strip().startswith("Candidate:"): candidate=line.split(":",1)[1].strip(); break
    rows.append({"package":item["package"],"expected":item["version"],"candidate":candidate})
bad=[row for row in rows if row["candidate"]!=row["expected"]]
json.dump({"schema":1,"packages":rows,"mismatches":bad},open(sys.argv[2],"w"),indent=2,sort_keys=True); open(sys.argv[2],"a").write("\n")
if bad: raise SystemExit("APT candidate versions do not match the exact proposed transaction")
PY
DEBIAN_FRONTEND=noninteractive apt-get -s -o Debug::pkgProblemResolver=yes -o APT::Get::AllowUnauthenticated=false install "${SEED[@]}" |& tee "${EVIDENCE}/apt-simulation.log"
DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Use-Pty=0 -o APT::Get::AllowUnauthenticated=false install "${SEED[@]}" |& tee "${EVIDENCE}/apt-install.log"
apt-get check |& tee "${EVIDENCE}/apt-check.log"
python3 - "${PAYLOAD}/install-seed.json" "${PAYLOAD}/frameworks-versions.json" "${EVIDENCE}/installed-versions.json" <<'PY'
import json,subprocess,sys
seed=json.load(open(sys.argv[1]))["packages"]; frameworks=json.load(open(sys.argv[2]))["packages"]
def version(package):
    proc=subprocess.run(["dpkg-query","-W","-f=${db:Status-Status}\t${Version}\n",package],text=True,capture_output=True)
    if proc.returncode!=0: return None
    status,value=proc.stdout.rstrip("\n").split("\t",1); return value if status=="installed" else None
seed_bad=[]
for item in seed:
    current=version(item["package"])
    if current!=item["version"]: seed_bad.append({"package":item["package"],"expected":item["version"],"installed":current})
frameworks_installed=[]; frameworks_bad=[]
for package,expected in frameworks.items():
    current=version(package)
    if current is None: continue
    frameworks_installed.append({"package":package,"expected":expected,"installed":current})
    if current!=expected: frameworks_bad.append({"package":package,"expected":expected,"installed":current})
result={"schema":1,"proposed_seed_count":len(seed),"proposed_mismatches":seed_bad,"frameworks_installed_count":len(frameworks_installed),"frameworks_installed":frameworks_installed,"frameworks_mismatches":frameworks_bad}
json.dump(result,open(sys.argv[3],"w"),indent=2,sort_keys=True); open(sys.argv[3],"a").write("\n")
if seed_bad: raise SystemExit("installed proposed package versions drifted")
if not frameworks_installed: raise SystemExit("clean transaction installed no admitted Frameworks packages")
if frameworks_bad: raise SystemExit("installed Frameworks packages include a partial/mismatched transition")
PY
python3 - "${PAYLOAD}/payload.json" "${EVIDENCE}/installed-versions.json" "${EVIDENCE}/result.json" "$(git -C "${ROOT}" rev-parse HEAD)" <<'PY'
import json,sys
payload=json.load(open(sys.argv[1])); installed=json.load(open(sys.argv[2]))
result={"schema":1,"state":"PASS","kind":"supralinux-proposed-integration-checkpoint","source_commit":sys.argv[4],"payload_source_commit":payload["source_commit"],"frameworks_pass_nodes":payload["frameworks_pass_nodes"],"proposed_candidate_count":payload["proposed_candidate_count"],"proposed_binary_seed_count":payload["proposed_binary_seed_count"],"frameworks_installed_count":installed["frameworks_installed_count"],"gates":{"apt_solvability":"PASS","dependency_closure":"PASS","clean_install":"PASS","upgrade_from_ubuntu":"NOT_RUN","abi_and_plugins":"NOT_RUN","representative_apps":"NOT_RUN","wayland_session":"NOT_RUN","integration_image":"NOT_RUN"},"partial_stack_transition":False,"package_attempts_complete":True,"package_attempt_consumed":False,"sbuild_invoked":False,"canonical_package_state_effect":"none","repository_active":False,"production_activation_eligible":False,"stable_publication_authorized":False}
json.dump(result,open(sys.argv[3],"w"),indent=2,sort_keys=True); open(sys.argv[3],"a").write("\n")
PY
(cd "${EVIDENCE}" && find . -type f ! -name evidence-sha256.txt -print0 | sort -z | xargs -0 sha256sum) > "${EVIDENCE}/evidence-sha256.txt"
printf 'SupraLINUX-proposed authoritative integration checkpoint: PASS\n'
printf 'gates=apt_solvability,dependency_closure,clean_install\n'
printf 'package_attempt_consumed=false\n'
printf 'sbuild_invoked=false\n'
