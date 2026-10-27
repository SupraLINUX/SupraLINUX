#!/usr/bin/env python3
"""Build a signed APT overlay from an exact SupraLINUX-proposed transaction plan."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def deb_field(path: Path, field: str, optional: bool = False) -> str:
    proc = subprocess.run(
        ["dpkg-deb", "-f", str(path), field],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        if optional:
            return ""
        raise SystemExit(f"dpkg-deb failed for {path}: {field}: {proc.stderr}")
    return proc.stdout.strip()


def dsc_fields(path: Path) -> dict:
    result = {}
    current = None
    for raw in path.read_text(errors="strict").splitlines():
        if raw.startswith((" ", "\t")) and current:
            result[current] += "\n" + raw.strip()
            continue
        if ":" in raw:
            current, value = raw.split(":", 1)
            result[current] = value.strip()
    return result


def locate_artifact(root: Path, digest: str) -> Path:
    direct = root / "sha256" / f"{digest}.zip"
    if direct.is_file() and sha256(direct) == digest:
        return direct
    matches = []
    for path in root.rglob("*.zip"):
        if sha256(path) == digest:
            matches.append(path)
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one artifact ZIP for {digest}, found {len(matches)}"
        )
    return matches[0]


def copy_verified(source: Path, target: Path, expected: str | None = None) -> str:
    digest = sha256(source)
    if expected and digest != expected:
        raise SystemExit(f"digest mismatch for {source}: {digest} != {expected}")
    if target.exists():
        if sha256(target) != digest:
            raise SystemExit(f"conflicting proposed payload filename: {target.name}")
        return digest
    shutil.copyfile(source, target)
    if sha256(target) != digest:
        raise SystemExit(f"copy verification failed: {target}")
    return digest


def build_indices(repo: Path, suite: str) -> tuple[Path, Path]:
    binary_dir = repo / "dists" / suite / "main" / "binary-amd64"
    source_dir = repo / "dists" / suite / "main" / "source"
    binary_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    packages = subprocess.check_output(
        ["apt-ftparchive", "packages", "pool"], cwd=repo, text=True
    )
    sources = subprocess.check_output(
        ["apt-ftparchive", "sources", "pool"], cwd=repo, text=True
    )
    packages_path = binary_dir / "Packages"
    sources_path = source_dir / "Sources"
    packages_path.write_text(packages)
    sources_path.write_text(sources)
    with (binary_dir / "Packages.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(packages.encode())
    with (source_dir / "Sources.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(sources.encode())

    release_dir = repo / "dists" / suite
    release = subprocess.check_output(
        [
            "apt-ftparchive",
            "-o", "APT::FTPArchive::Release::Origin=SupraLINUX",
            "-o", "APT::FTPArchive::Release::Label=SupraLINUX-proposed",
            "-o", f"APT::FTPArchive::Release::Suite={suite}",
            "-o", f"APT::FTPArchive::Release::Codename={suite}",
            "-o", "APT::FTPArchive::Release::Architectures=amd64",
            "-o", "APT::FTPArchive::Release::Components=main",
            "-o", "APT::FTPArchive::Release::Description=SupraLINUX proposed integration overlay",
            "release",
            ".",
        ],
        cwd=release_dir,
        text=True,
    )
    release_path = release_dir / "Release"
    release_path.write_text(release)
    return packages_path, release_path


def sign_release(repo: Path, suite: str, key: str) -> dict:
    release = repo / "dists" / suite / "Release"
    inrelease = release.with_name("InRelease")
    release_gpg = release.with_name("Release.gpg")
    subprocess.run(
        [
            "gpg", "--batch", "--yes", "--local-user", key,
            "--digest-algo", "SHA256", "--clearsign",
            "--output", str(inrelease), str(release),
        ],
        check=True,
    )
    subprocess.run(
        [
            "gpg", "--batch", "--yes", "--local-user", key,
            "--digest-algo", "SHA256", "--detach-sign",
            "--output", str(release_gpg), str(release),
        ],
        check=True,
    )
    fingerprint = subprocess.check_output(
        ["gpg", "--batch", "--with-colons", "--fingerprint", key], text=True
    )
    fprs = [line.split(":")[9] for line in fingerprint.splitlines() if line.startswith("fpr:")]
    if not fprs:
        raise SystemExit("unable to resolve repository signing fingerprint")
    return {
        "fingerprint": fprs[0],
        "inrelease_sha256": sha256(inrelease),
        "release_gpg_sha256": sha256(release_gpg),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signing-key")
    parser.add_argument("--unsigned-certification", action="store_true")
    args = parser.parse_args()

    if args.output.exists() or args.manifest.exists():
        raise SystemExit("refusing to replace an existing proposed repository or manifest")
    plan = json.loads(args.plan.read_text())
    if plan.get("state") != "PASS" or plan.get("kind") != "supralinux-proposed-transaction-plan":
        raise SystemExit("invalid proposed transaction plan")
    if plan.get("stable_publication_authorized") is not False:
        raise SystemExit("proposed plan must not authorize stable publication")
    if not args.signing_key and not args.unsigned_certification:
        raise SystemExit("signed proposed repositories require --signing-key")
    if args.signing_key and args.unsigned_certification:
        raise SystemExit("choose signed mode or unsigned certification mode, not both")

    suite = plan["suite"]
    pool = args.output / "pool" / "main"
    pool.mkdir(parents=True)
    candidates_manifest = []
    ignored_payloads = []

    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        for candidate in plan["candidates"]:
            artifact = locate_artifact(args.artifact_root, candidate["artifact_sha256"])
            if sha256(artifact) != candidate["artifact_sha256"]:
                raise SystemExit(f"artifact digest drift: {candidate['node']}")
            extracted = temp_root / candidate["node"]
            extracted.mkdir()
            with zipfile.ZipFile(artifact) as archive:
                archive.extractall(extracted)

            expected_binaries = candidate["binary_packages"]
            found_binaries = {}
            candidate_ignored = []
            for deb in sorted(extracted.rglob("*.deb")):
                package = deb_field(deb, "Package")
                version = deb_field(deb, "Version")
                architecture = deb_field(deb, "Architecture")
                source_field = deb_field(deb, "Source", optional=True)
                source_package = source_field.split(" ", 1)[0] if source_field else package

                if package not in expected_binaries:
                    candidate_ignored.append(str(deb.relative_to(extracted)))
                    continue
                if version != candidate["version"]:
                    raise SystemExit(
                        f"candidate version drift for {package}: {version} != {candidate['version']}"
                    )
                if architecture != expected_binaries[package]:
                    raise SystemExit(
                        f"candidate architecture drift for {package}: {architecture}"
                    )
                if source_package != candidate["source_package"]:
                    raise SystemExit(
                        f"candidate source drift for {package}: {source_package}"
                    )
                digest = sha256(deb)
                key = (package, architecture)
                if key in found_binaries and found_binaries[key]["sha256"] != digest:
                    raise SystemExit(f"conflicting duplicate candidate binary: {key}")
                target = pool / deb.name
                copy_verified(deb, target, digest)
                found_binaries[key] = {
                    "package": package,
                    "version": version,
                    "architecture": architecture,
                    "sha256": digest,
                    "repo_path": str(target.relative_to(args.output)),
                }

            expected_keys = {(name, arch) for name, arch in expected_binaries.items()}
            if set(found_binaries) != expected_keys:
                raise SystemExit(
                    f"candidate binary set mismatch for {candidate['node']}: "
                    f"expected={sorted(expected_keys)} actual={sorted(found_binaries)}"
                )

            dsc_matches = []
            for dsc in extracted.rglob("*.dsc"):
                fields = dsc_fields(dsc)
                if (
                    fields.get("Source") == candidate["source_package"]
                    and fields.get("Version") == candidate["version"]
                ):
                    dsc_matches.append((dsc, fields))
            if len(dsc_matches) != 1:
                raise SystemExit(
                    f"expected one exact .dsc for {candidate['node']}, found {len(dsc_matches)}"
                )
            dsc, fields = dsc_matches[0]
            source_dir = pool / candidate["source_package"][0] / candidate["source_package"]
            source_dir.mkdir(parents=True, exist_ok=True)
            dsc_digest = copy_verified(dsc, source_dir / dsc.name)
            source_files = [{"file": str((source_dir / dsc.name).relative_to(args.output)), "sha256": dsc_digest}]
            checksum_lines = fields.get("Checksums-Sha256", "").splitlines()
            if not checksum_lines:
                raise SystemExit(f".dsc lacks Checksums-Sha256: {candidate['node']}")
            for line in checksum_lines:
                parts = line.split()
                if len(parts) != 3:
                    raise SystemExit(f"invalid .dsc checksum line: {line!r}")
                expected_sha, _size, filename = parts
                source_file = dsc.parent / filename
                if not source_file.is_file():
                    matches = list(extracted.rglob(filename))
                    if len(matches) != 1:
                        raise SystemExit(f"missing source payload {filename}: {candidate['node']}")
                    source_file = matches[0]
                target = source_dir / filename
                digest = copy_verified(source_file, target, expected_sha)
                source_files.append({"file": str(target.relative_to(args.output)), "sha256": digest})

            candidates_manifest.append(
                {
                    "node": candidate["node"],
                    "source_package": candidate["source_package"],
                    "version": candidate["version"],
                    "artifact_id": candidate["artifact_id"],
                    "artifact_sha256": candidate["artifact_sha256"],
                    "result_path": candidate["result_path"],
                    "result_sha256": candidate["result_sha256"],
                    "binaries": sorted(found_binaries.values(), key=lambda row: row["package"]),
                    "source_files": source_files,
                    "ignored_artifact_debs": candidate_ignored,
                }
            )
            ignored_payloads.extend(
                {"node": candidate["node"], "path": item}
                for item in candidate_ignored
            )

    packages_path, release_path = build_indices(args.output, suite)
    signing = None
    if args.signing_key:
        signing = sign_release(args.output, suite, args.signing_key)

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "supralinux-proposed-repository",
        "suite": suite,
        "architecture": "amd64",
        "plan_path": str(args.plan),
        "plan_sha256": sha256(args.plan),
        "candidate_count": len(candidates_manifest),
        "candidates": candidates_manifest,
        "ignored_artifact_debs": ignored_payloads,
        "packages_sha256": sha256(packages_path),
        "release_sha256": sha256(release_path),
        "signed": signing is not None,
        "signing": signing,
        "activation_eligible": signing is not None,
        "stable_publication_authorized": False,
        "canonical_package_state_effect": "none",
        "package_attempt_consumed": False,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"SupraLINUX-proposed repository: PASS; candidates={len(candidates_manifest)} "
        f"signed={result['signed']}"
    )


if __name__ == "__main__":
    main()
