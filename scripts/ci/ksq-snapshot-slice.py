#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import lzma
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote, urlparse

SNAPSHOT = "20260829T022000Z"
BASE_URL = f"https://snapshot.ubuntu.com/ubuntu/{SNAPSHOT}"
FINAL_BASENAME = SNAPSHOT
STAGE_BASENAME = f".staging-{SNAPSHOT}"
KEYRING = Path("/usr/share/keyrings/ubuntu-archive-keyring.gpg")

SIZE_ARTIFACT_ID = "9781553137"
SIZE_ARTIFACT_DIGEST = "39672453ba364d81cfa8621cd060201f845a6d940fb4ac04d45aa25be1ce0e19"
KSQ0_ARTIFACT_ID = "9708738867"
KSQ0_ARTIFACT_DIGEST = "5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50"
BUILD_CONTAINER = "ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b"

EXPECTED_BINARY_OBJECTS = 1541
EXPECTED_BINARY_BYTES = 704826504
EXPECTED_UBUNTU_SOURCE_OBJECTS = 301
EXPECTED_UBUNTU_SOURCE_BYTES = 212283819
EXPECTED_DEBIAN_SOURCE_OBJECTS = 4
EXPECTED_DEBIAN_SOURCE_BYTES = 161155
EXPECTED_CERTIFIED_SEEDS = 244
EXPECTED_RAW_UPPER_BOUND = 1001129661

RESOLUTE_SUITES = ("resolute", "resolute-updates", "resolute-security", "resolute-backports")
COMPONENTS = ("main", "restricted", "universe", "multiverse")

DEBIAN_SOURCE_OBJECTS = {
    "wayland-protocols_1.48-1.dsc": (
        "6be63f02c5dbf851a22cef09c3f2b33074bd78d2",
        "f0b19a01b59a7501baef8360af45153d340997fa36e44ba322ff3d20b9ec253a",
    ),
    "wayland-protocols_1.48.orig.tar.xz": (
        "61a9d1f8454fa612a70f3a35b3a5f99471cba4ba",
        "398036ac0eb6484982ddbde7ff86848d753231f9cdeeae983f06b52946625aa1",
    ),
    "wayland-protocols_1.48.orig.tar.xz.asc": (
        "3f1d50a88477db8193debab281be9ca0b64d0dce",
        "421104518b8d370888d6a2f36c46281c1c9bc1203b69a12eeafe06ca38be4808",
    ),
    "wayland-protocols_1.48-1.debian.tar.xz": (
        "7eebc38bb402028be3de4e3d815037e3b601d25d",
        "d4dc3f6dd27526cb0993908707961511d80e952e1bf5c6635d3ba8c58f7faeac",
    ),
}


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_SNAPSHOT_SLICE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: list[str], *, capture: bool = False) -> str:
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
    if proc.returncode != 0:
        details = ""
        if capture:
            details = f"\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        fail(f"command failed ({proc.returncode}): {shlex.join(args)}{details}")
    return proc.stdout if capture else ""


def parse_deb822_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    key: str | None = None
    for raw in text.splitlines() + [""]:
        if not raw.strip():
            if current:
                records.append(current)
                current = {}
                key = None
            continue
        if raw[0].isspace() and key:
            current[key] += "\n" + raw[1:]
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        current[key] = value.lstrip()
    return records


def parse_clearsigned_payload(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("-----BEGIN PGP SIGNED MESSAGE-----")
    except ValueError:
        fail(f"not a clearsigned InRelease: {path}")
    i = start + 1
    while i < len(lines) and lines[i] != "":
        i += 1
    i += 1
    out: list[str] = []
    while i < len(lines) and lines[i] != "-----BEGIN PGP SIGNATURE-----":
        line = lines[i]
        if line.startswith("- "):
            line = line[2:]
        out.append(line)
        i += 1
    if i >= len(lines):
        fail(f"missing signature trailer in {path}")
    return "\n".join(out) + "\n"


def inrelease_sha256_map(path: Path) -> dict[str, tuple[int, str]]:
    payload = parse_clearsigned_payload(path)
    mapping: dict[str, tuple[int, str]] = {}
    in_sha256 = False
    for line in payload.splitlines():
        if line == "SHA256:":
            in_sha256 = True
            continue
        if in_sha256:
            if line and not line[0].isspace():
                break
            parts = line.split()
            if len(parts) == 3 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]) and parts[1].isdigit():
                mapping[parts[2]] = (int(parts[1]), parts[0].lower())
    if not mapping:
        fail(f"no SHA256 section parsed from {path}")
    return mapping


def verify_inrelease(path: Path) -> None:
    if not KEYRING.is_file():
        fail(f"Ubuntu archive keyring missing: {KEYRING}")
    run(["gpgv", "--keyring", str(KEYRING), str(path)])


def curl_download(url: str, dest: Path, expected_size: int | None = None, expected_hash: str | None = None, algorithm: str = "sha256") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        if (expected_size is None or dest.stat().st_size == expected_size) and (expected_hash is None or sha(dest, algorithm) == expected_hash):
            return
        fail(f"existing final object failed identity check: {dest}")
    part = dest.with_name(dest.name + ".part")

    def invoke(resume: bool) -> subprocess.CompletedProcess[bytes]:
        args = [
            "curl", "--fail", "--location", "--show-error", "--silent",
            "--retry", "10", "--retry-delay", "2", "--retry-all-errors",
            "--connect-timeout", "30",
        ]
        if resume:
            args += ["--continue-at", "-"]
        args += [url, "-o", str(part)]
        return subprocess.run(args)

    resume = part.is_file() and part.stat().st_size > 0
    proc = invoke(resume)
    # Curl exit 33 means the peer cannot satisfy a byte-range resume. In that
    # narrow case discard only the incomplete staging object and retry once
    # from byte zero; other transport failures retain the partial for reruns.
    if proc.returncode == 33 and resume:
        part.unlink(missing_ok=True)
        proc = invoke(False)
    if proc.returncode != 0:
        raise RuntimeError(f"curl rc={proc.returncode} url={url}")
    if expected_size is not None and part.stat().st_size != expected_size:
        bad = part.with_name(part.name + ".bad-size")
        part.replace(bad)
        raise RuntimeError(f"size mismatch {url}: expected={expected_size} got={bad.stat().st_size}")
    if expected_hash is not None:
        actual = sha(part, algorithm)
        if actual != expected_hash:
            bad = part.with_name(part.name + ".bad-hash")
            part.replace(bad)
            raise RuntimeError(f"{algorithm} mismatch {url}: expected={expected_hash} got={actual}")
    part.replace(dest)


def download_many(items: list[tuple[str, Path, int, str, str]], workers: int) -> None:
    errors: list[str] = []

    def one(item: tuple[str, Path, int, str, str]) -> None:
        url, dest, size, digest, algo = item
        curl_download(url, dest, size, digest, algo)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(one, item): item for item in items}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            item = futures[fut]
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{item[0]} :: {exc}")
            done += 1
            if done % 100 == 0 or done == len(items):
                print(f"AURORA_KSQ_SNAPSHOT_SLICE_DOWNLOAD_PROGRESS={done}/{len(items)}")
    if errors:
        for line in errors[:20]:
            print(line, file=sys.stderr)
        fail(f"{len(errors)} object download(s) failed; staging retained for resumable rerun")


def read_results_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v
    return out


def validate_canonical_evidence(size_dir: Path, ksq0_dir: Path, size_zip: Path, ksq0_zip: Path) -> None:
    if sha(size_zip) != SIZE_ARTIFACT_DIGEST:
        fail("size artifact ZIP digest mismatch")
    if sha(ksq0_zip) != KSQ0_ARTIFACT_DIGEST:
        fail("KSQ-0 closure artifact ZIP digest mismatch")
    results = read_results_env(size_dir / "results.env")
    expected = {
        "AURORA_KSQ_SLICE_STATUS": "MEASURED_METADATA_ONLY",
        "AURORA_KSQ_SLICE_SNAPSHOT": SNAPSHOT,
        "AURORA_KSQ_SLICE_CERTIFIED_BINARY_SEEDS": str(EXPECTED_CERTIFIED_SEEDS),
        "AURORA_KSQ_SLICE_BINARY_OBJECTS": str(EXPECTED_BINARY_OBJECTS),
        "AURORA_KSQ_SLICE_BINARY_BYTES": str(EXPECTED_BINARY_BYTES),
        "AURORA_KSQ_SLICE_UBUNTU_SOURCE_OBJECTS": str(EXPECTED_UBUNTU_SOURCE_OBJECTS),
        "AURORA_KSQ_SLICE_UBUNTU_SOURCE_BYTES": str(EXPECTED_UBUNTU_SOURCE_BYTES),
        "AURORA_KSQ_SLICE_DEBIAN_SOURCE_OBJECTS": str(EXPECTED_DEBIAN_SOURCE_OBJECTS),
        "AURORA_KSQ_SLICE_DEBIAN_SOURCE_BYTES": str(EXPECTED_DEBIAN_SOURCE_BYTES),
        "AURORA_KSQ_SLICE_RAW_UPPER_BOUND_BYTES": str(EXPECTED_RAW_UPPER_BOUND),
        "AURORA_KSQ_SLICE_PAYLOADS_DOWNLOADED": "0",
    }
    for k, v in expected.items():
        if results.get(k) != v:
            fail(f"canonical size evidence mismatch: {k} expected={v} got={results.get(k)!r}")
    closure = read_results_env(ksq0_dir / "build/ksq-0/closure-status.env")
    if closure.get("AURORA_KSQ_0_APT_SNAPSHOT") != SNAPSHOT or closure.get("AURORA_KSQ_0_CLOSURE_STATUS") != "COMPLETE":
        fail("KSQ-0 closure evidence is not COMPLETE for certified snapshot")


def metadata_targets() -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for suite in RESOLUTE_SUITES:
        for component in COMPONENTS:
            targets.append((suite, f"{component}/binary-amd64/Packages.xz"))
            targets.append((suite, f"{component}/source/Sources.xz"))
    for component in COMPONENTS:
        targets.append(("stonking", f"{component}/source/Sources.xz"))
    return targets


def materialize_metadata(stage: Path) -> dict[tuple[str, str], Path]:
    archive = stage / "ubuntu"
    result: dict[tuple[str, str], Path] = {}
    suites = list(RESOLUTE_SUITES) + ["stonking"]
    for suite in suites:
        rel = Path("dists") / suite / "InRelease"
        dest = archive / rel
        curl_download(f"{BASE_URL}/{rel.as_posix()}", dest)
        verify_inrelease(dest)
        result[(suite, "InRelease")] = dest

    for suite, rel_index in metadata_targets():
        inrelease = result[(suite, "InRelease")]
        entries = inrelease_sha256_map(inrelease)
        if rel_index not in entries:
            fail(f"signed InRelease does not contain required index {suite}/{rel_index}")
        size, digest = entries[rel_index]
        rel = Path("dists") / suite / rel_index
        dest = archive / rel
        curl_download(f"{BASE_URL}/{rel.as_posix()}", dest, size, digest, "sha256")
        result[(suite, rel_index)] = dest
        by_hash = dest.parent / "by-hash" / "SHA256" / digest
        by_hash.parent.mkdir(parents=True, exist_ok=True)
        if by_hash.exists():
            if sha(by_hash) != digest:
                fail(f"existing by-hash object mismatch: {by_hash}")
        else:
            os.link(dest, by_hash)
    return result


def package_index_map(meta: dict[tuple[str, str], Path]) -> dict[str, dict[str, str]]:
    by_filename: dict[str, dict[str, str]] = {}
    for suite in RESOLUTE_SUITES:
        for component in COMPONENTS:
            path = meta[(suite, f"{component}/binary-amd64/Packages.xz")]
            with lzma.open(path, "rt", encoding="utf-8", errors="strict") as f:
                records = parse_deb822_records(f.read())
            for rec in records:
                filename = rec.get("Filename")
                if not filename:
                    continue
                required = ("Package", "Version", "Architecture", "Size", "SHA256")
                if any(k not in rec for k in required):
                    continue
                row = {k: rec[k] for k in required}
                row["suite"] = suite
                row["component"] = component
                row["Filename"] = filename
                previous = by_filename.get(filename)
                if previous and (previous["Size"], previous["SHA256"]) != (row["Size"], row["SHA256"]):
                    fail(f"same binary Filename has conflicting identity: {filename}")
                if not previous:
                    by_filename[filename] = row
    return by_filename


def selected_binary_paths(size_dir: Path) -> dict[str, tuple[int, str]]:
    selected: dict[str, tuple[int, str]] = {}
    prefix = f"/ubuntu/{SNAPSHOT}/"
    for line in (size_dir / "binary-print-uris.txt").read_text(encoding="utf-8").splitlines():
        if not line.startswith("'"):
            continue
        fields = shlex.split(line)
        if len(fields) < 3 or not fields[2].isdigit():
            continue
        url = fields[0]
        parsed = urlparse(url)
        path = unquote(parsed.path)
        if prefix not in path:
            fail(f"binary URI is outside certified snapshot: {url}")
        rel = path.split(prefix, 1)[1]
        if not rel.startswith("pool/") or not rel.endswith(".deb"):
            fail(f"unexpected binary object path: {rel}")
        size = int(fields[2])
        previous = selected.get(rel)
        if previous and previous[0] != size:
            fail(f"binary object appears with conflicting size: {rel}")
        selected[rel] = (size, url)
    if len(selected) != EXPECTED_BINARY_OBJECTS:
        fail(f"binary object count mismatch from canonical size artifact: {len(selected)}")
    if sum(size for size, _ in selected.values()) != EXPECTED_BINARY_BYTES:
        fail("binary byte total mismatch from canonical size artifact")
    return selected


def materialize_binaries(stage: Path, size_dir: Path, meta: dict[tuple[str, str], Path], workers: int) -> list[dict[str, str]]:
    package_map = package_index_map(meta)
    selected = selected_binary_paths(size_dir)
    jobs: list[tuple[str, Path, int, str, str]] = []
    rows: list[dict[str, str]] = []
    for rel in sorted(selected):
        size_from_uri, url = selected[rel]
        rec = package_map.get(rel)
        if not rec:
            fail(f"selected binary object missing from signed local Packages metadata: {rel}")
        size = int(rec["Size"])
        if size != size_from_uri:
            fail(f"selected binary size differs from signed Packages metadata: {rel}")
        digest = rec["SHA256"].lower()
        jobs.append((url, stage / "ubuntu" / rel, size, digest, "sha256"))
        rows.append({
            "path": f"ubuntu/{rel}", "size": str(size), "sha256": digest,
            "package": rec["Package"], "version": rec["Version"], "architecture": rec["Architecture"],
            "suite": rec["suite"], "component": rec["component"],
        })
    download_many(jobs, workers)
    return rows


def source_index_map(meta: dict[tuple[str, str], Path]) -> dict[tuple[str, str], list[dict[str, str]]]:
    result: dict[tuple[str, str], list[dict[str, str]]] = {}
    suites = list(RESOLUTE_SUITES) + ["stonking"]
    for suite in suites:
        for component in COMPONENTS:
            key = (suite, f"{component}/source/Sources.xz")
            path = meta.get(key)
            if not path:
                continue
            with lzma.open(path, "rt", encoding="utf-8", errors="strict") as f:
                for rec in parse_deb822_records(f.read()):
                    pkg, version = rec.get("Package"), rec.get("Version")
                    if pkg and version:
                        rec = dict(rec)
                        rec["_suite"] = suite
                        rec["_component"] = component
                        result.setdefault((pkg, version), []).append(rec)
    return result


@dataclass(frozen=True)
class SourceObject:
    source: str
    version: str
    origin: str
    path: str
    size: int
    sha512: str


def parse_selected_source_records(path: Path) -> list[tuple[str, str, str, dict[str, str]]]:
    sections: list[tuple[str, str, str, dict[str, str]]] = []
    current_header: tuple[str, str, str] | None = None
    current_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines() + ["### __END__ 0 origin=end"]:
        if line.startswith("### "):
            if current_header:
                records = parse_deb822_records("\n".join(current_lines) + "\n")
                if len(records) != 1:
                    fail(f"cannot parse canonical source record for {current_header[0]}")
                sections.append((*current_header, records[0]))
            if line.startswith("### __END__"):
                current_header = None
                break
            m = re.fullmatch(r"### (\S+) (\S+) origin=(\S+)", line)
            if not m:
                fail(f"invalid canonical source header: {line}")
            current_header = (m.group(1), m.group(2), m.group(3))
            current_lines = []
        elif current_header:
            current_lines.append(line)
    return sections


def checksum_rows(value: str, expected_len: int) -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for line in value.splitlines():
        parts = line.split()
        if len(parts) == 3 and len(parts[0]) == expected_len and parts[1].isdigit():
            out[parts[2]] = (int(parts[1]), parts[0].lower())
    return out


def materialize_ubuntu_sources(stage: Path, ksq0_dir: Path, meta: dict[tuple[str, str], Path], workers: int) -> list[dict[str, str]]:
    index = source_index_map(meta)
    canonical = parse_selected_source_records(ksq0_dir / "build/ksq-0/selected-source-records.txt")
    objects: dict[str, SourceObject] = {}
    for source, version, origin, rec in canonical:
        if origin == "debian-source":
            continue
        if origin not in {f"ubuntu-stonking@{SNAPSHOT}", "ubuntu-stonking-snapshot"}:
            fail(f"unexpected Ubuntu source origin in canonical closure: {source} {origin}")
        candidates = [r for r in index.get((source, version), []) if r.get("_suite") == "stonking"]
        if len(candidates) != 1:
            fail(f"expected exactly one signed stonking source record for {source}={version}, found {len(candidates)}")
        signed = candidates[0]
        for field in ("Directory", "Checksums-Sha512"):
            if rec.get(field, "").strip() != signed.get(field, "").strip():
                fail(f"canonical source record differs from signed stonking {field}: {source}={version}")
        directory = rec.get("Directory", "")
        hashes = checksum_rows(rec.get("Checksums-Sha512", ""), 128)
        if not directory or not hashes:
            fail(f"missing source object identity fields: {source}={version}")
        for name, (size, digest) in hashes.items():
            rel = f"{directory}/{name}"
            obj = SourceObject(source, version, origin, rel, size, digest)
            prev = objects.get(rel)
            if prev and (prev.size, prev.sha512) != (size, digest):
                fail(f"conflicting source object identity: {rel}")
            objects[rel] = obj
    if len(objects) != EXPECTED_UBUNTU_SOURCE_OBJECTS:
        fail(f"Ubuntu source object count mismatch: {len(objects)}")
    if sum(o.size for o in objects.values()) != EXPECTED_UBUNTU_SOURCE_BYTES:
        fail("Ubuntu source byte total mismatch")
    jobs: list[tuple[str, Path, int, str, str]] = []
    rows: list[dict[str, str]] = []
    for rel, obj in sorted(objects.items()):
        url = f"{BASE_URL}/{rel}"
        jobs.append((url, stage / "ubuntu" / rel, obj.size, obj.sha512, "sha512"))
        rows.append({
            "path": f"ubuntu/{rel}", "size": str(obj.size), "sha512": obj.sha512,
            "source": obj.source, "version": obj.version, "origin": obj.origin,
        })
    download_many(jobs, workers)
    return rows


def materialize_debian_source(stage: Path, ksq0_dir: Path) -> list[dict[str, str]]:
    audit = ksq0_dir / "build/ksq-0/source-audit/downloads"
    out = stage / "debian-sources/wayland-protocols-1.48"
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    total = 0
    for name, (sha1_id, expected_sha256) in sorted(DEBIAN_SOURCE_OBJECTS.items()):
        src = audit / name
        if not src.is_file() or sha(src) != expected_sha256:
            fail(f"canonical Debian source object missing or hash mismatch: {name}")
        dest = out / name
        if dest.exists():
            if sha(dest) != expected_sha256:
                fail(f"existing Debian source object mismatch: {dest}")
        else:
            shutil.copy2(src, dest)
        size = dest.stat().st_size
        total += size
        rows.append({
            "path": f"debian-sources/wayland-protocols-1.48/{name}", "size": str(size),
            "sha256": expected_sha256, "snapshot_sha1": sha1_id,
            "url": f"https://snapshot.debian.org/file/{sha1_id}",
        })
    if len(rows) != EXPECTED_DEBIAN_SOURCE_OBJECTS or total != EXPECTED_DEBIAN_SOURCE_BYTES:
        fail(f"Debian source size/count mismatch: count={len(rows)} bytes={total}")
    return rows


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("\t".join(fields) + "\n")
        for row in rows:
            f.write("\t".join(row.get(k, "") for k in fields) + "\n")


def write_local_sources(stage: Path, final_path: Path) -> None:
    text = f"""Types: deb deb-src
URIs: file:{final_path}/ubuntu
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no

Types: deb-src
URIs: file:{final_path}/ubuntu
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
"""
    (stage / "aurora-local.sources").write_text(text, encoding="utf-8")


def copy_provenance(stage: Path, size_zip: Path, ksq0_zip: Path, size_dir: Path, ksq0_dir: Path) -> None:
    out = stage / "provenance"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(size_zip, out / f"github-artifact-{SIZE_ARTIFACT_ID}.zip")
    shutil.copy2(ksq0_zip, out / f"github-artifact-{KSQ0_ARTIFACT_ID}.zip")
    for src, name in [
        (size_dir / "results.env", "size-probe-results.env"),
        (size_dir / "certified-binary-seeds.tsv", "certified-binary-seeds.tsv"),
        (ksq0_dir / "build/ksq-0/closure-status.env", "ksq0-closure-status.env"),
        (ksq0_dir / "build/ksq-0/selected-source-records.txt", "selected-source-records.txt"),
        (ksq0_dir / "build/ksq-0/apt-metadata.sha256", "ksq0-apt-metadata.sha256"),
        (ksq0_dir / "build/ksq-0/source-audit/wayland-protocols-1.48.sha256", "wayland-protocols-1.48.sha256"),
    ]:
        shutil.copy2(src, out / name)


def metadata_manifest_rows(stage: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for p in sorted((stage / "ubuntu/dists").rglob("*")):
        if not p.is_file() or "/by-hash/" in p.as_posix():
            continue
        rel = p.relative_to(stage).as_posix()
        rows.append({"path": rel, "size": str(p.stat().st_size), "sha256": sha(p)})
    return rows


def write_provenance_env(stage: Path, binary_rows: list[dict[str, str]], source_rows: list[dict[str, str]], debian_rows: list[dict[str, str]], metadata_rows: list[dict[str, str]]) -> None:
    content = "\n".join([
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS=COMPLETE",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SNAPSHOT={SNAPSHOT}",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH=amd64",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BUILD_CONTAINER={BUILD_CONTAINER}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_ID={SIZE_ARTIFACT_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_SHA256={SIZE_ARTIFACT_DIGEST}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_ID={KSQ0_ARTIFACT_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_SHA256={KSQ0_ARTIFACT_DIGEST}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS={len(binary_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_BYTES={sum(int(r['size']) for r in binary_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_OBJECTS={len(source_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_BYTES={sum(int(r['size']) for r in source_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_OBJECTS={len(debian_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_BYTES={sum(int(r['size']) for r in debian_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_OBJECTS={len(metadata_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BYTES={sum(int(r['size']) for r in metadata_rows)}",
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK=forbidden",
        "AURORA_KSQ_SNAPSHOT_SLICE_APT_SNAPSHOT_MODE=disabled-local-copy",
        "",
    ])
    (stage / "provenance.env").write_text(content, encoding="utf-8")


def harden_read_only(root: Path) -> None:
    for p in sorted(root.rglob("*"), reverse=True):
        if p.is_symlink():
            fail(f"slice contains symlink, which is forbidden: {p}")
        if p.is_dir():
            os.chmod(p, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        elif p.is_file():
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.chmod(root, 0o555)


def read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        fail(f"empty manifest: {path}")
    fields = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(fields):
            fail(f"malformed TSV row in {path}: {line}")
        rows.append(dict(zip(fields, parts)))
    return rows


def validate_slice(final: Path, *, check_read_only: bool = True) -> None:
    if not final.is_dir():
        fail(f"slice path missing: {final}")
    symlinks = [p for p in final.rglob("*") if p.is_symlink()]
    if symlinks:
        fail(f"slice contains symlink, which is forbidden: {symlinks[0]}")
    env = read_results_env(final / "provenance.env")
    required = {
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS": "COMPLETE",
        "AURORA_KSQ_SNAPSHOT_SLICE_SNAPSHOT": SNAPSHOT,
        "AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_ID": SIZE_ARTIFACT_ID,
        "AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_SHA256": SIZE_ARTIFACT_DIGEST,
        "AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_ID": KSQ0_ARTIFACT_ID,
        "AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_SHA256": KSQ0_ARTIFACT_DIGEST,
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK": "forbidden",
    }
    for k, v in required.items():
        if env.get(k) != v:
            fail(f"slice provenance mismatch: {k}")
    if sha(final / f"provenance/github-artifact-{SIZE_ARTIFACT_ID}.zip") != SIZE_ARTIFACT_DIGEST:
        fail("retained size artifact digest mismatch")
    if sha(final / f"provenance/github-artifact-{KSQ0_ARTIFACT_ID}.zip") != KSQ0_ARTIFACT_DIGEST:
        fail("retained KSQ-0 artifact digest mismatch")

    manifests = final / "manifests"
    binary = read_tsv(manifests / "binary.tsv")
    ubuntu_source = read_tsv(manifests / "ubuntu-source.tsv")
    debian_source = read_tsv(manifests / "debian-source.tsv")
    metadata = read_tsv(manifests / "metadata.tsv")
    if len(binary) != EXPECTED_BINARY_OBJECTS or sum(int(r["size"]) for r in binary) != EXPECTED_BINARY_BYTES:
        fail("binary manifest count/bytes mismatch")
    if len(ubuntu_source) != EXPECTED_UBUNTU_SOURCE_OBJECTS or sum(int(r["size"]) for r in ubuntu_source) != EXPECTED_UBUNTU_SOURCE_BYTES:
        fail("Ubuntu source manifest count/bytes mismatch")
    if len(debian_source) != EXPECTED_DEBIAN_SOURCE_OBJECTS or sum(int(r["size"]) for r in debian_source) != EXPECTED_DEBIAN_SOURCE_BYTES:
        fail("Debian source manifest count/bytes mismatch")

    expected_pool: set[str] = set()
    for row in binary:
        p = final / row["path"]
        expected_pool.add(row["path"])
        if not p.is_file() or p.stat().st_size != int(row["size"]) or sha(p) != row["sha256"]:
            fail(f"binary object validation failed: {row['path']}")
    for row in ubuntu_source:
        p = final / row["path"]
        expected_pool.add(row["path"])
        if not p.is_file() or p.stat().st_size != int(row["size"]) or sha(p, "sha512") != row["sha512"]:
            fail(f"Ubuntu source object validation failed: {row['path']}")
    for row in debian_source:
        p = final / row["path"]
        if not p.is_file() or p.stat().st_size != int(row["size"]) or sha(p) != row["sha256"]:
            fail(f"Debian source object validation failed: {row['path']}")

    expected_metadata: set[str] = set()
    expected_by_hash: set[str] = set()
    for row in metadata:
        p = final / row["path"]
        expected_metadata.add(row["path"])
        if not p.is_file() or p.stat().st_size != int(row["size"]) or sha(p) != row["sha256"]:
            fail(f"metadata object validation failed: {row['path']}")
        if p.name in {"Packages.xz", "Sources.xz"}:
            by_hash = p.parent / "by-hash" / "SHA256" / row["sha256"]
            rel_by_hash = by_hash.relative_to(final).as_posix()
            expected_by_hash.add(rel_by_hash)
            if not by_hash.is_file() or by_hash.stat().st_size != p.stat().st_size or sha(by_hash) != row["sha256"]:
                fail(f"by-hash metadata validation failed: {rel_by_hash}")
            if not os.path.samefile(p, by_hash):
                fail(f"by-hash object is not the expected hardlink: {rel_by_hash}")

    actual_metadata = {
        p.relative_to(final).as_posix()
        for p in (final / "ubuntu/dists").rglob("*")
        if p.is_file()
    }
    allowed_metadata = expected_metadata | expected_by_hash
    if actual_metadata != allowed_metadata:
        extra = sorted(actual_metadata - allowed_metadata)[:10]
        missing = sorted(allowed_metadata - actual_metadata)[:10]
        fail(f"metadata whitelist mismatch; extra={extra} missing={missing}")

    actual_pool = {p.relative_to(final).as_posix() for p in (final / "ubuntu/pool").rglob("*") if p.is_file()}
    if actual_pool != expected_pool:
        extra = sorted(actual_pool - expected_pool)[:10]
        missing = sorted(expected_pool - actual_pool)[:10]
        fail(f"pool whitelist mismatch; extra={extra} missing={missing}")

    for suite in list(RESOLUTE_SUITES) + ["stonking"]:
        verify_inrelease(final / "ubuntu/dists" / suite / "InRelease")
    sources_text = (final / "aurora-local.sources").read_text(encoding="utf-8")
    expected_uri = f"URIs: file:{final}/ubuntu"
    if sources_text.count(expected_uri) != 2 or "Snapshot: no" not in sources_text or "http://" in sources_text or "https://" in sources_text:
        fail("local APT source is not strictly local/fail-closed")
    if check_read_only:
        writable = [p for p in [final, *final.rglob("*")] if p.exists() and (p.stat().st_mode & 0o222)]
        if writable:
            fail(f"slice contains writable paths, e.g. {writable[0]}")
    print("AURORA_KSQ_SNAPSHOT_SLICE_VALID")


def materialize(args: argparse.Namespace) -> None:
    root = args.archive_root.resolve()
    final = root / FINAL_BASENAME
    stage = root / STAGE_BASENAME
    if final.exists():
        validate_slice(final)
        print("AURORA_KSQ_SNAPSHOT_SLICE_ALREADY_COMPLETE")
        return
    root.mkdir(parents=True, exist_ok=True)
    stage.mkdir(parents=True, exist_ok=True)
    validate_canonical_evidence(args.size_artifact_dir, args.ksq0_artifact_dir, args.size_artifact_zip, args.ksq0_artifact_zip)
    copy_provenance(stage, args.size_artifact_zip, args.ksq0_artifact_zip, args.size_artifact_dir, args.ksq0_artifact_dir)
    meta = materialize_metadata(stage)
    binary_rows = materialize_binaries(stage, args.size_artifact_dir, meta, args.workers)
    source_rows = materialize_ubuntu_sources(stage, args.ksq0_artifact_dir, meta, args.workers)
    debian_rows = materialize_debian_source(stage, args.ksq0_artifact_dir)
    metadata_rows = metadata_manifest_rows(stage)
    write_tsv(stage / "manifests/binary.tsv", ["path", "size", "sha256", "package", "version", "architecture", "suite", "component"], binary_rows)
    write_tsv(stage / "manifests/ubuntu-source.tsv", ["path", "size", "sha512", "source", "version", "origin"], source_rows)
    write_tsv(stage / "manifests/debian-source.tsv", ["path", "size", "sha256", "snapshot_sha1", "url"], debian_rows)
    write_tsv(stage / "manifests/metadata.tsv", ["path", "size", "sha256"], metadata_rows)
    write_local_sources(stage, final)
    write_provenance_env(stage, binary_rows, source_rows, debian_rows, metadata_rows)
    (stage / "COMPLETE").write_text("AURORA_KSQ_SNAPSHOT_SLICE_COMPLETE\n", encoding="utf-8")
    validate_slice(stage, check_read_only=False)
    harden_read_only(stage)
    os.replace(stage, final)
    validate_slice(final)
    print(f"AURORA_KSQ_SNAPSHOT_SLICE_PATH={final}")
    print("AURORA_KSQ_SNAPSHOT_SLICE_MATERIALIZED")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_mat = sub.add_parser("materialize")
    p_mat.add_argument("--archive-root", type=Path, default=Path("/srv/supralinux/archive"))
    p_mat.add_argument("--size-artifact-dir", type=Path, required=True)
    p_mat.add_argument("--ksq0-artifact-dir", type=Path, required=True)
    p_mat.add_argument("--size-artifact-zip", type=Path, required=True)
    p_mat.add_argument("--ksq0-artifact-zip", type=Path, required=True)
    p_mat.add_argument("--workers", type=int, default=6)
    p_val = sub.add_parser("validate")
    p_val.add_argument("--slice-root", type=Path, default=Path(f"/srv/supralinux/archive/{SNAPSHOT}"))
    args = parser.parse_args()
    if args.command == "materialize":
        materialize(args)
    else:
        validate_slice(args.slice_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
