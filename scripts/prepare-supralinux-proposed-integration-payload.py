#!/usr/bin/env python3
"""Prepare an exact signed Frameworks + Plasma payload for authoritative KVM integration."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build-supralinux-proposed.py"

def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, stdout=None) -> None:
    subprocess.run(args, cwd=cwd, env=env, stdout=stdout, check=True)

def parse_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        if not raw:
            continue
        if "=" not in raw:
            raise SystemExit(f"invalid key/value line in {path}: {raw!r}")
        key, value = raw.split("=", 1)
        if not key or key in result:
            raise SystemExit(f"invalid or duplicate key in {path}: {key!r}")
        result[key] = value
    return result

def load_builder():
    spec = importlib.util.spec_from_file_location("supralinux_proposed_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load proposed repository builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def fingerprint(env: dict[str, str], cwd: Path) -> str:
    output = subprocess.check_output(["gpg","--batch","--with-colons","--list-secret-keys"],cwd=cwd,env=env,text=True)
    values = [line.split(":")[9] for line in output.splitlines() if line.startswith("fpr:")]
    if len(values) != 1:
        raise SystemExit(f"expected one ephemeral integration signing key, found {len(values)}")
    return values[0]

def render_frameworks_release(builder, release_dir: Path, suite: str) -> str:
    indexed = sorted(path for path in release_dir.rglob("*") if path.is_file() and path.name not in {"Release","InRelease","Release.gpg"})
    if not indexed:
        raise SystemExit("Frameworks integration repository has no indices")
    lines = [
        "Origin: SupraLINUX","Label: SupraLINUX-frameworks",f"Suite: {suite}",f"Codename: {suite}",
        "Architectures: amd64","Components: main","Description: SupraLINUX Frameworks 6.30 admitted integration base",
        f"Date: {formatdate(0, usegmt=True)}",
    ]
    for label, algorithm in (("MD5Sum","md5"),("SHA1","sha1"),("SHA256","sha256")):
        lines.append(f"{label}:")
        for path in indexed:
            lines.append(f" {builder.file_digest(path, algorithm)} {path.stat().st_size} {path.relative_to(release_dir).as_posix()}")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout",type=Path,required=True)
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--frameworks-image",type=Path,required=True)
    parser.add_argument("--frameworks-provenance",type=Path,required=True)
    parser.add_argument("--work-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-commit",required=True)
    args=parser.parse_args()

    if args.work_dir.exists() or args.output.exists():
        raise SystemExit("refusing to reuse integration payload paths")
    if not args.artifact_root.is_dir() or args.artifact_root.is_symlink():
        raise SystemExit("persistent artifact root is missing or invalid")
    if not args.frameworks_image.is_file() or args.frameworks_image.is_symlink():
        raise SystemExit("Frameworks milestone image is missing or invalid")
    if not args.frameworks_provenance.is_file() or args.frameworks_provenance.is_symlink():
        raise SystemExit("Frameworks milestone provenance is missing or invalid")
    if len(args.source_commit)!=40 or any(ch not in "0123456789abcdef" for ch in args.source_commit):
        raise SystemExit("invalid source commit")
    for command in ("git","gpg","gpgv","dpkg-deb","python3"):
        if shutil.which(command) is None:
            raise SystemExit(f"missing integration payload command: {command}")

    resolved=subprocess.check_output(["git","-C",str(args.checkout),"rev-parse","HEAD"],text=True).strip()
    if resolved != args.source_commit:
        raise SystemExit("integration payload checkout does not match source commit")
    dirty=subprocess.check_output(["git","-C",str(args.checkout),"status","--porcelain","--untracked-files=normal"],text=True)
    if dirty:
        raise SystemExit("integration payload checkout is not clean")

    content_cert=json.loads((args.checkout/"manifests/supralinux-proposed-content-certification.json").read_text())
    signing_cert=json.loads((args.checkout/"manifests/supralinux-proposed-signing-certification.json").read_text())
    integration=json.loads((args.checkout/"manifests/supralinux-proposed-integration.json").read_text())
    if content_cert.get("state")!="PASS" or signing_cert.get("state")!="PASS":
        raise SystemExit("sealed proposed content/signing certification is not PASS")
    if signing_cert.get("verification",{}).get("signature_verification")!="PASS":
        raise SystemExit("sealed proposed signing verification is not PASS")
    if signing_cert.get("verification",{}).get("private_signing_key_retained") is not False:
        raise SystemExit("sealed signing evidence does not prove private-key disposal")
    if signing_cert.get("invariants",{}).get("production_activation_eligible") is not False:
        raise SystemExit("integration must start from a non-activating certification repository")
    if integration.get("state")!="prepared-inactive" or integration.get("promotion",{}).get("authorized") is not False:
        raise SystemExit("integration manifest is not prepared-inactive")

    run(["scripts/check-frameworks-milestone-image.sh",str(args.frameworks_image)],cwd=args.checkout)
    provenance=parse_kv(args.frameworks_provenance)
    if not (
        provenance.get("kind")=="frameworks-milestone-execution-cache"
        and provenance.get("cache_only")=="yes"
        and provenance.get("canonical_source_of_truth")=="no"
        and provenance.get("frameworks_series")=="6.30.0"
        and provenance.get("pass_nodes")=="65"
        and provenance.get("framework_packages_preinstalled_in_sbuild_rootfs")=="no"
    ):
        raise SystemExit("Frameworks milestone provenance contract mismatch")

    builder=load_builder()
    args.work_dir.mkdir(parents=True,mode=0o700)
    args.output.mkdir(parents=True,mode=0o755)
    repos=args.output/"repos"; repos.mkdir(mode=0o755)
    frameworks_repo=repos/"frameworks"
    proposed_repo=repos/"proposed"
    extracted_parent=args.work_dir/"frameworks-extracted"; extracted_parent.mkdir()

    run(["scripts/with-libguestfs-runtime.sh","virt-copy-out","-a",str(args.frameworks_image),"/var/lib/supralinux/milestones/frameworks-6.30",str(extracted_parent)],cwd=args.checkout)
    milestone=extracted_parent/"frameworks-6.30"
    source_frameworks_repo=milestone/"repo"
    checkpoint=parse_kv(milestone/"checkpoint-manifest.txt")
    package_pool=json.loads((milestone/"package-pool.json").read_text())
    if checkpoint.get("packages_index_sha256")!=provenance.get("packages_index_sha256"):
        raise SystemExit("Frameworks checkpoint/provenance Packages digest mismatch")
    if sha256(source_frameworks_repo/"Packages")!=provenance["packages_index_sha256"]:
        raise SystemExit("Frameworks cached Packages digest mismatch")
    if sha256(milestone/"package-pool.json")!=provenance.get("package_pool_sha256"):
        raise SystemExit("Frameworks package-pool digest mismatch")
    if package_pool.get("kind")!="frameworks-6.30-binary-pool" or package_pool.get("package_count",0)<=0:
        raise SystemExit("invalid Frameworks package pool")
    for path in milestone.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"Frameworks milestone payload contains symlink: {path}")
    shutil.copytree(source_frameworks_repo,frameworks_repo)

    frameworks_suite="resolute-supralinux-frameworks"
    binary_dir=frameworks_repo/"dists"/frameworks_suite/"main"/"binary-amd64"
    binary_dir.mkdir(parents=True)
    packages_text=(frameworks_repo/"Packages").read_text()
    (binary_dir/"Packages").write_text(packages_text)
    builder.write_gzip(binary_dir/"Packages.gz",packages_text)
    release_dir=frameworks_repo/"dists"/frameworks_suite
    release_path=release_dir/"Release"
    release_path.write_text(render_frameworks_release(builder,release_dir,frameworks_suite))

    plan=args.work_dir/"proposed-plan.json"
    run(["python3","scripts/plan-supralinux-proposed.py","--output",str(plan)],cwd=args.checkout)
    if sha256(plan)!=content_cert["certification"]["plan_sha256"]:
        raise SystemExit("current proposed plan differs from sealed content certification")
    proposed_plan=json.loads(plan.read_text())
    if proposed_plan.get("candidate_count")!=24 or proposed_plan.get("base_stack",{}).get("frameworks_pass_nodes")!=65:
        raise SystemExit("unexpected proposed integration candidate/base count")

    gnupg=args.work_dir/"gnupg"; gnupg.mkdir(mode=0o700)
    env=os.environ.copy(); env["GNUPGHOME"]=str(gnupg)
    identity="SupraLINUX integration certification <integration@supralinux.invalid>"
    public_key=args.output/"certification-public-key.gpg"
    proposed_manifest=args.output/"proposed-repository.json"
    try:
        run(["gpg","--batch","--passphrase","","--quick-generate-key",identity,"ed25519","sign","0"],cwd=args.checkout,env=env)
        key_fingerprint=fingerprint(env,args.checkout)
        with public_key.open("wb") as output:
            run(["gpg","--batch","--export",key_fingerprint],cwd=args.checkout,env=env,stdout=output)
        if not public_key.stat().st_size:
            raise SystemExit("empty integration public key")
        old_gnupg=os.environ.get("GNUPGHOME"); os.environ["GNUPGHOME"]=str(gnupg)
        try:
            frameworks_signing=builder.sign_release(frameworks_repo,frameworks_suite,key_fingerprint)
        finally:
            if old_gnupg is None: os.environ.pop("GNUPGHOME",None)
            else: os.environ["GNUPGHOME"]=old_gnupg
        run(["python3","scripts/build-supralinux-proposed.py","--plan",str(plan),"--artifact-root",str(args.artifact_root),"--output",str(proposed_repo),"--manifest",str(proposed_manifest),"--signing-key",key_fingerprint,"--signed-certification"],cwd=args.checkout,env=env)
    finally:
        if gnupg.exists(): shutil.rmtree(gnupg)

    proposed_receipt=json.loads(proposed_manifest.read_text())
    if not (
        proposed_receipt.get("state")=="PASS"
        and proposed_receipt.get("signed") is True
        and proposed_receipt.get("certification_mode")=="signed"
        and proposed_receipt.get("activation_eligible") is False
        and proposed_receipt.get("stable_publication_authorized") is False
        and proposed_receipt.get("package_attempt_consumed") is False
    ):
        raise SystemExit("proposed integration repository receipt contract mismatch")

    proposed_suite=proposed_plan["suite"]
    proposed_release=proposed_repo/"dists"/proposed_suite/"Release"
    proposed_packages=proposed_repo/"dists"/proposed_suite/"main"/"binary-amd64"/"Packages"
    proposed_sources=proposed_repo/"dists"/proposed_suite/"main"/"source"/"Sources"
    for path,expected in (
        (proposed_packages,signing_cert["certification"]["packages_sha256"]),
        (proposed_sources,signing_cert["certification"]["sources_sha256"]),
        (proposed_release,signing_cert["certification"]["release_sha256"]),
    ):
        if sha256(path)!=expected:
            raise SystemExit(f"proposed integration content differs from sealed certification: {path}")

    for repo_dir,suite in ((frameworks_repo,frameworks_suite),(proposed_repo,proposed_suite)):
        inrelease=repo_dir/"dists"/suite/"InRelease"
        detached=repo_dir/"dists"/suite/"Release.gpg"
        release=repo_dir/"dists"/suite/"Release"
        run(["gpgv","--keyring",str(public_key),str(inrelease)],cwd=args.checkout)
        run(["gpgv","--keyring",str(public_key),str(detached),str(release)],cwd=args.checkout)

    seed=[]; seen_seed=set()
    for candidate in proposed_plan["candidates"]:
        for package,architecture in sorted(candidate["binary_packages"].items()):
            if package in seen_seed: raise SystemExit(f"duplicate proposed integration package: {package}")
            seen_seed.add(package)
            seed.append({"package":package,"version":candidate["version"],"architecture":architecture,"node":candidate["node"]})
    framework_versions={}
    for item in package_pool["packages"]:
        package=item["package"]; version=item["version"]; architecture=item["architecture"]
        if architecture not in {"amd64","all"}: continue
        previous=framework_versions.get(package)
        if previous is not None and previous!=version:
            raise SystemExit(f"multiple Frameworks versions for {package}: {previous} vs {version}")
        framework_versions[package]=version
    if not framework_versions: raise SystemExit("Frameworks integration version map is empty")

    (args.output/"install-seed.json").write_text(json.dumps({"schema":1,"packages":seed},indent=2,sort_keys=True)+"\n")
    (args.output/"frameworks-versions.json").write_text(json.dumps({"schema":1,"packages":framework_versions},indent=2,sort_keys=True)+"\n")
    shutil.copyfile(plan,args.output/"proposed-plan.json")
    payload={
        "schema":1,"state":"PASS","kind":"supralinux-proposed-integration-payload","source_commit":args.source_commit,
        "frameworks_suite":frameworks_suite,"proposed_suite":proposed_suite,"frameworks_pass_nodes":65,
        "proposed_candidate_count":24,"proposed_binary_seed_count":len(seed),"frameworks_binary_package_count":len(framework_versions),
        "frameworks_packages_sha256":sha256(binary_dir/"Packages"),"frameworks_release_sha256":sha256(release_path),
        "frameworks_inrelease_sha256":frameworks_signing["inrelease_sha256"],"frameworks_release_gpg_sha256":frameworks_signing["release_gpg_sha256"],
        "proposed_plan_sha256":sha256(plan),"proposed_packages_sha256":sha256(proposed_packages),"proposed_sources_sha256":sha256(proposed_sources),
        "proposed_release_sha256":sha256(proposed_release),"public_key_sha256":sha256(public_key),
        "signing_fingerprint":frameworks_signing["fingerprint"],"signature_verification":"PASS",
        "ephemeral_signing_key":True,"private_signing_key_retained":False,"repository_active":False,
        "production_activation_eligible":False,"stable_publication_authorized":False,"canonical_package_state_effect":"none",
        "package_attempt_consumed":False,"sbuild_invoked":False,
    }
    if payload["signing_fingerprint"]!=proposed_receipt["signing"]["fingerprint"]:
        raise SystemExit("Frameworks/proposed integration repositories use different signing keys")
    (args.output/"payload.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    for path in args.output.rglob("*"):
        if path.is_symlink(): raise SystemExit(f"integration payload contains symlink: {path}")
        path.chmod(0o755 if path.is_dir() else 0o644)
    args.output.chmod(0o755)
    print(f"SupraLINUX-proposed integration payload: PASS; proposed={len(seed)} frameworks={len(framework_versions)}")

if __name__=="__main__":
    main()
