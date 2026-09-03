#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import lzma
import re
import shlex
import subprocess
from pathlib import Path
from typing import NoReturn
from urllib.parse import quote

SNAPSHOT = "20260829T022000Z"
BASE_URL = f"https://snapshot.ubuntu.com/ubuntu/{SNAPSHOT}"
EXTENSION_ID = "20260829T022000Z-kwallet-runtime-r1"
KEYRING = Path("/usr/share/keyrings/ubuntu-archive-keyring.gpg")
EXPECTED_ACQUISITIONS = 375
EXPECTED_R2_BINARY_OBJECTS = 1783

# package, version, architecture, pool path, suite, component
EXPECTED_GAP = (
    (
        "lsb-base",
        "11.6build1",
        "all",
        "pool/main/l/lsb/lsb-base_11.6build1_all.deb",
        "resolute",
        "main",
    ),
    (
        "libwrap0",
        "7.6.q-36build2",
        "amd64",
        "pool/main/t/tcp-wrappers/libwrap0_7.6.q-36build2_amd64.deb",
        "resolute",
        "main",
    ),
    (
        "socat",
        "1.8.1.1-1ubuntu0.1",
        "amd64",
        "pool/main/s/socat/socat_1.8.1.1-1ubuntu0.1_amd64.deb",
        "resolute-updates",
        "main",
    ),
)
EXPECTED_MISSING = {(p, v, a, path) for p, v, a, path, _, _ in EXPECTED_GAP}

ACQUIRE_RE = re.compile(r"^(Get|Err|Ign):(\d+)\s+(.+)$")
ERR_RE = re.compile(
    r"^file:\S+\s+(?P<suite>\S+)\s+(?P<index_arch>\S+)\s+"
    r"(?P<package>\S+)\s+(?P<package_arch>\S+)\s+(?P<version>\S+)$"
)
PATH_VERSION_RE = re.compile(r"^(?P<prefix>.+)_(?P<version>[^_]+)_(?P<arch>[^_]+)\.deb$")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_FAILURE: {message}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: list[str], *, capture: bool = False) -> str:
    cp = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if cp.returncode != 0:
        detail = ""
        if capture:
            detail = f"\nstdout:\n{cp.stdout}\nstderr:\n{cp.stderr}"
        fail(f"command failed ({cp.returncode}): {shlex.join(args)}{detail}")
    return cp.stdout if capture else ""


def curl_download(
    url: str,
    dest: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.unlink(missing_ok=True)
    cp = subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--show-error",
            "--silent",
            "--retry",
            "10",
            "--retry-delay",
            "2",
            "--retry-all-errors",
            "--connect-timeout",
            "30",
            url,
            "-o",
            str(part),
        ],
        check=False,
    )
    if cp.returncode != 0:
        fail(f"curl failed ({cp.returncode}): {url}")
    if expected_size is not None and part.stat().st_size != expected_size:
        fail(
            f"size mismatch for {url}: expected={expected_size} "
            f"got={part.stat().st_size}"
        )
    if expected_sha256 is not None:
        actual = sha256_file(part)
        if actual != expected_sha256:
            fail(
                f"SHA-256 mismatch for {url}: expected={expected_sha256} "
                f"got={actual}"
            )
    part.replace(dest)


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
    in_section = False
    for line in payload.splitlines():
        if line == "SHA256:":
            in_section = True
            continue
        if in_section:
            if line and not line[0].isspace():
                break
            fields = line.split()
            if (
                len(fields) == 3
                and re.fullmatch(r"[0-9a-fA-F]{64}", fields[0])
                and fields[1].isdigit()
            ):
                mapping[fields[2]] = (int(fields[1]), fields[0].lower())
    if not mapping:
        fail(f"no SHA256 section parsed from {path}")
    return mapping


def verify_inrelease(path: Path) -> None:
    if not KEYRING.is_file():
        fail(f"Ubuntu archive keyring missing: {KEYRING}")
    run(["gpgv", "--keyring", str(KEYRING), str(path)])


def dpkg_field(deb: Path, field: str) -> str:
    return run(["dpkg-deb", "-f", str(deb), field], capture=True).strip()


def parse_r2_objects(path: Path) -> set[str]:
    objects: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        fields = raw.split("\t")
        if len(fields) != 2 or not fields[1].isdigit():
            fail(f"invalid r2 object row at line {line_no}: {raw!r}")
        if fields[0] in objects:
            fail(f"duplicate r2 object path: {fields[0]}")
        objects.add(fields[0])
    if len(objects) != EXPECTED_R2_BINARY_OBJECTS:
        fail(
            f"expected {EXPECTED_R2_BINARY_OBJECTS} r2 binary objects, "
            f"got {len(objects)}"
        )
    return objects


def infer_pool_path(package: str, version: str, arch: str, error_detail: str) -> str:
    marker = "File not found - "
    if marker not in error_detail:
        fail(f"missing file path detail for {package}")
    absolute = error_detail.split(marker, 1)[1].split(" (", 1)[0]
    needle = "/ubuntu/"
    if needle not in absolute:
        fail(f"unexpected missing object path for {package}: {absolute}")
    pool_path = absolute.split(needle, 1)[1]
    basename = Path(pool_path).name
    m = PATH_VERSION_RE.match(basename)
    if not m or m.group("version") != version or m.group("arch") != arch:
        fail(
            f"missing object filename does not match "
            f"{package}={version}:{arch}: {basename}"
        )
    return pool_path


def validate_gap_files(root: Path) -> None:
    gap_tsv = root / "runtime-gap.tsv"
    status = root / "gap-status.env"
    if not gap_tsv.is_file() or not status.is_file():
        fail("runtime gap evidence missing")

    rows = gap_tsv.read_text(encoding="utf-8").splitlines()
    expected_header = (
        "package\tversion\tarchitecture\tpool_path\t"
        "suite\tacquisition_index\tr2_present"
    )
    if not rows or rows[0] != expected_header:
        fail("runtime-gap.tsv header mismatch")

    actual: set[tuple[str, str, str, str, str]] = set()
    for raw in rows[1:]:
        fields = raw.split("\t")
        if len(fields) != 7:
            fail(f"invalid runtime-gap.tsv row: {raw!r}")
        p, v, a, path, suite, index, present = fields
        if not index.isdigit() or present != "no":
            fail(f"invalid runtime-gap.tsv state: {raw!r}")
        actual.add((p, v, a, path, suite))
    expected = {
        (p, v, a, path, f"{suite}/{component}")
        for p, v, a, path, suite, component in EXPECTED_GAP
    }
    if actual != expected or len(rows) != len(EXPECTED_GAP) + 1:
        fail(f"runtime gap evidence mismatch: {sorted(actual)!r}")

    status_lines = set(status.read_text(encoding="utf-8").splitlines())
    required = {
        "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_STATUS=PROVEN",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_GAP_SNAPSHOT={SNAPSHOT}",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS={EXPECTED_ACQUISITIONS}",
        "AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_PRESENT=372",
        "AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_MISSING=3",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_R2_BINARY_OBJECTS={EXPECTED_R2_BINARY_OBJECTS}",
        "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_PACKAGES=lsb-base,libwrap0,socat",
    }
    missing = sorted(required - status_lines)
    if missing:
        fail(f"runtime gap status contract missing: {missing}")


def analyze(args: argparse.Namespace) -> None:
    solver_log = Path(args.solver_log)
    r2_objects_path = Path(args.r2_binary_objects)
    out = Path(args.out_dir)
    if not solver_log.is_file() or not r2_objects_path.is_file():
        fail("analysis inputs missing")
    out.mkdir(parents=True, exist_ok=True)

    lines = solver_log.read_text(encoding="utf-8", errors="replace").splitlines()
    by_index: dict[int, list[tuple[str, str, str | None]]] = {}
    for pos, line in enumerate(lines):
        m = ACQUIRE_RE.match(line)
        if not m:
            continue
        kind, index_text, rest = m.groups()
        index = int(index_text)
        detail = None
        if (
            kind == "Err"
            and pos + 1 < len(lines)
            and lines[pos + 1].startswith("  ")
        ):
            detail = lines[pos + 1].strip()
        by_index.setdefault(index, []).append((kind, rest, detail))

    expected_indices = set(range(1, EXPECTED_ACQUISITIONS + 1))
    actual_indices = set(by_index)
    if actual_indices != expected_indices:
        missing = sorted(expected_indices - actual_indices)
        extra = sorted(actual_indices - expected_indices)
        fail(f"acquisition index coverage mismatch missing={missing} extra={extra}")

    final_get = 0
    final_err: list[tuple[str, str, str, str, str, str]] = []
    for index in range(1, EXPECTED_ACQUISITIONS + 1):
        records = by_index[index]
        if any(kind == "Err" for kind, _, _ in records):
            err_records = [
                (rest, detail)
                for kind, rest, detail in records
                if kind == "Err"
            ]
            if len(err_records) != 1:
                fail(f"acquisition {index} has {len(err_records)} Err records")
            rest, detail = err_records[0]
            m = ERR_RE.match(rest)
            if not m or detail is None:
                fail(f"cannot parse Err acquisition {index}: {rest}")
            package = m.group("package")
            version = m.group("version")
            package_arch = m.group("package_arch")
            pool_path = infer_pool_path(package, version, package_arch, detail)
            final_err.append(
                (
                    package,
                    version,
                    package_arch,
                    pool_path,
                    m.group("suite"),
                    str(index),
                )
            )
        elif any(kind == "Get" for kind, _, _ in records):
            final_get += 1
        else:
            fail(f"acquisition {index} ended without Get or Err")

    if final_get != EXPECTED_ACQUISITIONS - len(EXPECTED_MISSING):
        fail(f"expected 372 successful acquisitions, got {final_get}")
    actual_missing = {(p, v, a, path) for p, v, a, path, _, _ in final_err}
    if actual_missing != EXPECTED_MISSING:
        fail(f"runtime gap mismatch: {sorted(actual_missing)!r}")

    expected_suite = {
        (p, v, a, path): f"{suite}/{component}"
        for p, v, a, path, suite, component in EXPECTED_GAP
    }
    for p, v, a, path, suite, _ in final_err:
        if expected_suite[(p, v, a, path)] != suite:
            fail(
                f"runtime gap suite mismatch for {p}: "
                f"expected={expected_suite[(p, v, a, path)]} got={suite}"
            )

    r2_objects = parse_r2_objects(r2_objects_path)
    for package, version, arch, pool_path, _, _ in final_err:
        if pool_path in r2_objects:
            fail(f"reported missing object is present in r2 manifest: {pool_path}")

    gap_tsv = out / "runtime-gap.tsv"
    with gap_tsv.open("w", encoding="utf-8") as f:
        f.write(
            "package\tversion\tarchitecture\tpool_path\t"
            "suite\tacquisition_index\tr2_present\n"
        )
        for row in sorted(final_err):
            package, version, arch, pool_path, suite, index = row
            f.write(
                f"{package}\t{version}\t{arch}\t{pool_path}\t"
                f"{suite}\t{index}\tno\n"
            )

    status = out / "gap-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_STATUS=PROVEN",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_GAP_SNAPSHOT={SNAPSHOT}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS={EXPECTED_ACQUISITIONS}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_PRESENT={final_get}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_MISSING={len(final_err)}",
                (
                    "AURORA_KSQ_1_KWALLET_RUNTIME_R2_BINARY_OBJECTS="
                    f"{EXPECTED_R2_BINARY_OBJECTS}"
                ),
                "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_PACKAGES=lsb-base,libwrap0,socat",
                "",
            ]
        ),
        encoding="utf-8",
    )
    validate_gap_files(out)
    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_KWALLET_RUNTIME_GAP_ANALYSIS_SUCCESS")


def package_index_contract(
    metadata_root: Path,
    suite: str,
    component: str,
    *,
    download: bool,
) -> tuple[Path, Path]:
    suite_root = metadata_root / suite
    inrelease = suite_root / "InRelease"
    packages_xz = suite_root / component / "binary-amd64" / "Packages.xz"
    index_rel = f"{component}/binary-amd64/Packages.xz"

    if download:
        curl_download(f"{BASE_URL}/dists/{suite}/InRelease", inrelease)
    if not inrelease.is_file():
        fail(f"InRelease missing for {suite}")
    verify_inrelease(inrelease)

    sha_map = inrelease_sha256_map(inrelease)
    if index_rel not in sha_map:
        fail(f"{suite} InRelease does not enumerate {index_rel}")
    expected_size, expected_sha = sha_map[index_rel]

    if download:
        curl_download(
            f"{BASE_URL}/dists/{suite}/{index_rel}",
            packages_xz,
            expected_size=expected_size,
            expected_sha256=expected_sha,
        )
    if not packages_xz.is_file():
        fail(f"Packages.xz missing for {suite}/{component}")
    if packages_xz.stat().st_size != expected_size:
        fail(f"Packages.xz size mismatch for {suite}/{component}")
    if sha256_file(packages_xz) != expected_sha:
        fail(f"Packages.xz SHA-256 mismatch for {suite}/{component}")

    return inrelease, packages_xz


def find_package_record(
    packages_xz: Path,
    package: str,
    version: str,
    arch: str,
) -> dict[str, str]:
    try:
        text = lzma.decompress(packages_xz.read_bytes()).decode("utf-8")
    except (lzma.LZMAError, UnicodeDecodeError) as exc:
        fail(f"cannot decode {packages_xz}: {exc}")
    matches = [
        record
        for record in parse_deb822_records(text)
        if record.get("Package") == package
        and record.get("Version") == version
        and record.get("Architecture") == arch
    ]
    if len(matches) != 1:
        fail(
            f"expected one signed package record for "
            f"{package}={version}:{arch}, got {len(matches)}"
        )
    return matches[0]


def validate_snapshot_contract(root: Path, *, download: bool) -> None:
    metadata_root = root / "metadata"
    packages_dir = root / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)

    cache: dict[tuple[str, str], Path] = {}
    package_rows: list[tuple[str, str, str, str, int, str, str]] = []

    for package, version, arch, pool_path, suite, component in EXPECTED_GAP:
        key = (suite, component)
        if key not in cache:
            _, packages_xz = package_index_contract(
                metadata_root,
                suite,
                component,
                download=download,
            )
            cache[key] = packages_xz

        record = find_package_record(cache[key], package, version, arch)
        if record.get("Filename") != pool_path:
            fail(
                f"signed Filename mismatch for {package}: "
                f"expected={pool_path} got={record.get('Filename')!r}"
            )
        record_sha = record.get("SHA256", "")
        record_size = record.get("Size", "")
        if not re.fullmatch(r"[0-9a-f]{64}", record_sha):
            fail(f"signed SHA256 missing/invalid for {package}")
        if not record_size.isdigit():
            fail(f"signed Size missing/invalid for {package}")
        expected_size = int(record_size)

        dest = packages_dir / Path(pool_path).name
        if download:
            curl_download(
                f"{BASE_URL}/{quote(pool_path, safe='/')}",
                dest,
                expected_size=expected_size,
                expected_sha256=record_sha,
            )
        if not dest.is_file():
            fail(f"extension package missing: {dest.name}")
        if dest.stat().st_size != expected_size:
            fail(f"extension package size mismatch: {dest.name}")
        if sha256_file(dest) != record_sha:
            fail(f"extension package SHA-256 mismatch: {dest.name}")
        if dpkg_field(dest, "Package") != package:
            fail(f"DEB Package mismatch: {dest.name}")
        if dpkg_field(dest, "Version") != version:
            fail(f"DEB Version mismatch: {dest.name}")
        if dpkg_field(dest, "Architecture") != arch:
            fail(f"DEB Architecture mismatch: {dest.name}")

        package_rows.append(
            (package, version, arch, pool_path, expected_size, record_sha, suite)
        )

    sha_manifest = root / "packages.sha256"
    if download:
        sha_manifest.write_text(
            "".join(
                f"{sha}  packages/{Path(pool_path).name}\n"
                for _, _, _, pool_path, _, sha, _ in sorted(package_rows)
            ),
            encoding="utf-8",
        )
    if not sha_manifest.is_file():
        fail("packages.sha256 missing")
    manifest_lines = sha_manifest.read_text(encoding="utf-8").splitlines()
    expected_lines = sorted(
        f"{sha}  packages/{Path(pool_path).name}"
        for _, _, _, pool_path, _, sha, _ in package_rows
    )
    if sorted(manifest_lines) != expected_lines:
        fail("packages.sha256 contract mismatch")

    metadata_hashes = root / "snapshot-metadata.sha256"
    metadata_files = sorted(p for p in metadata_root.rglob("*") if p.is_file())
    if download:
        metadata_hashes.write_text(
            "".join(
                f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n"
                for path in metadata_files
            ),
            encoding="utf-8",
        )
    if not metadata_hashes.is_file():
        fail("snapshot-metadata.sha256 missing")
    expected_meta = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in metadata_files
    }
    actual_meta: dict[str, str] = {}
    for raw in metadata_hashes.read_text(encoding="utf-8").splitlines():
        fields = raw.split(None, 1)
        if len(fields) != 2:
            fail(f"invalid snapshot-metadata.sha256 row: {raw!r}")
        digest, rel = fields
        rel = rel.lstrip("* ")
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            fail(f"unsafe metadata hash path: {rel}")
        actual_meta[rel] = digest
    if actual_meta != expected_meta:
        fail("snapshot metadata hash manifest mismatch")


def materialize(args: argparse.Namespace) -> None:
    root = Path(args.root)
    if not root.is_dir():
        fail("materialization root missing")
    validate_gap_files(root)

    provenance = root / "provenance.env"
    packages_dir = root / "packages"
    metadata_root = root / "metadata"
    if packages_dir.exists() or metadata_root.exists() or provenance.exists():
        fail("materialization output already exists; refusing overwrite")

    validate_snapshot_contract(root, download=True)

    provenance.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS=IMMUTABLE",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
                (
                    "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT="
                    f"{SNAPSHOT}"
                ),
                "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES=3",
                "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ARCH=amd64+all",
                (
                    "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SOURCE="
                    "ubuntu-snapshot-service"
                ),
                f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_BASE_URL={BASE_URL}",
                (
                    "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SUITES="
                    "resolute,resolute-updates"
                ),
                "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_COMPONENT=main",
                (
                    "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES_LIST="
                    "lsb-base,libwrap0,socat"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    validate_root(root)
    print("AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_MATERIALIZED")


def validate_root(root: Path) -> None:
    packages_dir = root / "packages"
    gap_tsv = root / "runtime-gap.tsv"
    status = root / "gap-status.env"
    sha_manifest = root / "packages.sha256"
    provenance = root / "provenance.env"
    metadata_manifest = root / "snapshot-metadata.sha256"

    for path in (
        packages_dir,
        gap_tsv,
        status,
        sha_manifest,
        provenance,
        metadata_manifest,
    ):
        if not path.exists():
            fail(f"extension member missing: {path.name}")

    validate_gap_files(root)

    debs = sorted(packages_dir.glob("*.deb"))
    if len(debs) != 3:
        fail(f"expected exactly 3 extension DEBs, got {len(debs)}")

    actual: set[tuple[str, str, str]] = set()
    for deb in debs:
        package = dpkg_field(deb, "Package")
        version = dpkg_field(deb, "Version")
        arch = dpkg_field(deb, "Architecture")
        actual.add((package, version, arch))
    expected = {(p, v, a) for p, v, a, _, _, _ in EXPECTED_GAP}
    if actual != expected:
        fail(f"extension package identities mismatch: {sorted(actual)!r}")

    provenance_text = provenance.read_text(encoding="utf-8")
    required = {
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS=IMMUTABLE",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
        (
            "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT="
            f"{SNAPSHOT}"
        ),
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES=3",
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ARCH=amd64+all",
        (
            "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SOURCE="
            "ubuntu-snapshot-service"
        ),
        f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_BASE_URL={BASE_URL}",
        (
            "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SUITES="
            "resolute,resolute-updates"
        ),
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_COMPONENT=main",
        (
            "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES_LIST="
            "lsb-base,libwrap0,socat"
        ),
    }
    lines = set(provenance_text.splitlines())
    missing_required = sorted(required - lines)
    if missing_required:
        fail(f"provenance contract missing: {missing_required}")

    validate_snapshot_contract(root, download=False)
    print("AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_VALID")


def validate(args: argparse.Namespace) -> None:
    validate_root(Path(args.root))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze")
    p.add_argument("--solver-log", required=True)
    p.add_argument("--r2-binary-objects", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=analyze)

    p = sub.add_parser("materialize")
    p.add_argument("--root", required=True)
    p.set_defaults(func=materialize)

    p = sub.add_parser("validate")
    p.add_argument("--root", required=True)
    p.set_defaults(func=validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
