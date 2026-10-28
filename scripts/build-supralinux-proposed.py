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
from email.utils import formatdate
from pathlib import Path


def file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    return file_digest(path, "sha256")


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


def dsc_payload(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0] != "-----BEGIN PGP SIGNED MESSAGE-----":
        return text.strip() + "\n"
    index = 1
    while index < len(lines) and lines[index]:
        index += 1
    if index >= len(lines):
        raise SystemExit("invalid clearsigned .dsc header")
    index += 1
    payload = []
    while index < len(lines) and lines[index] != "-----BEGIN PGP SIGNATURE-----":
        line = lines[index]
        if line.startswith("- "):
            line = line[2:]
        payload.append(line)
        index += 1
    if index >= len(lines):
        raise SystemExit("invalid clearsigned .dsc signature")
    return "\n".join(payload).strip() + "\n"


def parse_deb822(text: str) -> list[tuple[str, list[str]]]:
    fields: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for raw in text.splitlines():
        if not raw:
            continue
        if raw.startswith((" ", "\t")):
            if current is None:
                raise SystemExit("invalid Deb822 continuation without a field")
            current.append(raw)
            continue
        if ":" not in raw:
            raise SystemExit(f"invalid Deb822 field line: {raw!r}")
        name, value = raw.split(":", 1)
        if not name or any(ch.isspace() for ch in name):
            raise SystemExit(f"invalid Deb822 field name: {name!r}")
        current = [value.lstrip()]
        fields.append((name, current))
    return fields


def dsc_fields(path: Path) -> dict[str, str]:
    return {
        name: "\n".join(line.strip() for line in values)
        for name, values in parse_deb822(dsc_payload(path.read_text(errors="strict")))
    }


def dsc_sha256_entries(
    fields: dict[str, str],
    node: str,
) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for line in fields.get("Checksums-Sha256", "").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 3:
            raise SystemExit(f"invalid .dsc checksum line: {line!r}")
        entries.append((parts[0], parts[1], parts[2]))
    if not entries:
        raise SystemExit(f".dsc lacks Checksums-Sha256: {node}")
    return entries


def locate_artifact(
    root: Path,
    digest: str,
    archive_root: str | None = None,
) -> Path:
    if archive_root:
        relative = Path(archive_root)
        if (
            not relative.parts
            or relative.parts[0] != ".artifacts"
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise SystemExit(f"invalid retained artifact root: {archive_root}")
        retained = root.joinpath(*relative.parts[1:]) / "sha256" / f"{digest}.zip"
        if not retained.is_file() or retained.is_symlink():
            raise SystemExit(f"retained artifact is missing: {retained}")
        if sha256(retained) != digest:
            raise SystemExit(f"retained artifact digest drift: {retained}")
        return retained

    direct = root / "sha256" / f"{digest}.zip"
    if direct.is_file() and not direct.is_symlink() and sha256(direct) == digest:
        return direct
    matches = []
    for path in root.rglob("*.zip"):
        if path.is_file() and not path.is_symlink() and sha256(path) == digest:
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


def render_binary_packages(repo: Path) -> str:
    stanzas = []
    for deb in sorted(repo.glob("pool/**/*.deb")):
        control = subprocess.check_output(
            ["dpkg-deb", "--field", str(deb)],
            text=True,
        ).strip()
        fields = {name for name, _values in parse_deb822(control)}
        forbidden = {"Filename", "Size", "MD5sum", "SHA1", "SHA256"} & fields
        if forbidden:
            raise SystemExit(
                f"binary control contains repository-owned fields: {sorted(forbidden)}"
            )
        relative = deb.relative_to(repo).as_posix()
        stanza = [
            control,
            f"Filename: {relative}",
            f"Size: {deb.stat().st_size}",
            f"MD5sum: {file_digest(deb, 'md5')}",
            f"SHA1: {file_digest(deb, 'sha1')}",
            f"SHA256: {sha256(deb)}",
        ]
        stanzas.append("\n".join(stanza))
    if not stanzas:
        raise SystemExit("proposed repository contains no binary packages")
    return "\n\n".join(stanzas) + "\n"


def render_source_stanza(repo: Path, dsc: Path) -> str:
    parsed = parse_deb822(dsc_payload(dsc.read_text(errors="strict")))
    fields = {name: values for name, values in parsed}
    source = fields.get("Source")
    version = fields.get("Version")
    if not source or not source[0] or not version or not version[0]:
        raise SystemExit(f"source metadata missing Source/Version: {dsc}")
    if "Directory" in fields:
        raise SystemExit(f".dsc unexpectedly owns repository Directory field: {dsc}")

    source_dir = dsc.parent
    source_files = sorted(
        path for path in source_dir.iterdir()
        if path.is_file() and not path.is_symlink()
    )
    if dsc not in source_files:
        raise SystemExit(f"source .dsc is not in its repository directory: {dsc}")

    output = []
    for name, values in parsed:
        if name in {"Files", "Checksums-Sha1", "Checksums-Sha256", "Directory"}:
            continue
        rendered_name = "Package" if name == "Source" else name
        output.append(f"{rendered_name}: {values[0]}")
        output.extend(values[1:])

    output.append(f"Directory: {source_dir.relative_to(repo).as_posix()}")
    for label, algorithm in (
        ("Files", "md5"),
        ("Checksums-Sha1", "sha1"),
        ("Checksums-Sha256", "sha256"),
    ):
        output.append(f"{label}:")
        for path in source_files:
            output.append(
                f" {file_digest(path, algorithm)} {path.stat().st_size} {path.name}"
            )
    return "\n".join(output)


def render_sources(repo: Path) -> str:
    stanzas = [
        render_source_stanza(repo, dsc)
        for dsc in sorted(repo.glob("pool/**/*.dsc"))
    ]
    if not stanzas:
        raise SystemExit("proposed repository contains no source packages")
    identities = []
    for stanza in stanzas:
        fields = {
            name: "\n".join(line.strip() for line in values)
            for name, values in parse_deb822(stanza)
        }
        identities.append((fields.get("Package"), fields.get("Version")))
    if len(set(identities)) != len(identities):
        raise SystemExit("proposed repository contains duplicate source identities")
    return "\n\n".join(stanzas) + "\n"


def write_gzip(path: Path, content: str) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(content.encode())


def render_release(
    release_dir: Path,
    suite: str,
    source_date_epoch: int = 0,
) -> str:
    indexed = sorted(
        path for path in release_dir.rglob("*")
        if path.is_file()
        and path.name not in {"Release", "InRelease", "Release.gpg"}
    )
    if not indexed:
        raise SystemExit("proposed repository release has no indices")
    lines = [
        "Origin: SupraLINUX",
        "Label: SupraLINUX-proposed",
        f"Suite: {suite}",
        f"Codename: {suite}",
        "Architectures: amd64",
        "Components: main",
        "Description: SupraLINUX proposed integration overlay",
        f"Date: {formatdate(source_date_epoch, usegmt=True)}",
    ]
    for label, algorithm in (
        ("MD5Sum", "md5"),
        ("SHA1", "sha1"),
        ("SHA256", "sha256"),
    ):
        lines.append(f"{label}:")
        for path in indexed:
            lines.append(
                f" {file_digest(path, algorithm)} {path.stat().st_size} "
                f"{path.relative_to(release_dir).as_posix()}"
            )
    return "\n".join(lines) + "\n"


def source_date_epoch() -> int:
    raw = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid SOURCE_DATE_EPOCH: {raw!r}") from exc
    if value < 0:
        raise SystemExit("SOURCE_DATE_EPOCH must be non-negative")
    return value


def build_indices(repo: Path, suite: str) -> tuple[Path, Path]:
    binary_dir = repo / "dists" / suite / "main" / "binary-amd64"
    source_dir = repo / "dists" / suite / "main" / "source"
    binary_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    packages = render_binary_packages(repo)
    sources = render_sources(repo)
    packages_path = binary_dir / "Packages"
    sources_path = source_dir / "Sources"
    packages_path.write_text(packages)
    sources_path.write_text(sources)
    write_gzip(binary_dir / "Packages.gz", packages)
    write_gzip(source_dir / "Sources.gz", sources)

    release_dir = repo / "dists" / suite
    release_path = release_dir / "Release"
    release_path.write_text(
        render_release(release_dir, suite, source_date_epoch())
    )
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
            retention = candidate.get("retention") or {}
            artifact = locate_artifact(
                args.artifact_root,
                candidate["artifact_sha256"],
                retention.get("archive_root"),
            )
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
            for expected_sha, _size, filename in dsc_sha256_entries(
                fields, candidate["node"]
            ):
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
