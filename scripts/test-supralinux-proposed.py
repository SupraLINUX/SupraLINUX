#!/usr/bin/env python3
import gzip
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts/plan-supralinux-proposed.py"
BUILDER = ROOT / "scripts/build-supralinux-proposed.py"
PROMOTER = ROOT / "scripts/evaluate-supralinux-proposed-promotion.py"
CONFIG = ROOT / "manifests/supralinux-proposed.json"
PLASMA = ROOT / "manifests/kde-plasma-package-build.json"

with tempfile.TemporaryDirectory() as td:
    plan = Path(td) / "plan.json"
    subprocess.run(
        ["python3", str(PLANNER), "--output", str(plan)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(plan.read_text())
    plasma = json.loads(PLASMA.read_text())
    expected = {
        node
        for node, record in plasma["nodes"].items()
        if record.get("state") == "PASS"
        and not record.get("compatibility_hold")
        and any(item.get("state") == "PASS" for item in record.get("attempts", []))
    }
    actual = {item["node"] for item in payload["candidates"]}
    assert actual == expected, (sorted(expected - actual), sorted(actual - expected))

    candidates = {item["node"]: item for item in payload["candidates"]}
    for retained_only in ("kactivitymanagerd", "plasma-workspace-wallpapers"):
        candidate = candidates[retained_only]
        assert candidate["artifact_id"] is None
        assert candidate["artifact_sha256"]
        assert candidate["retention"]["artifact_zip_sha256_verified"] is True
        assert candidate["retention"]["offline_restore_verified"] is True
        assert candidate["retention"]["requires_github_for_restore"] is False

    assert "drkonqi" not in actual
    assert "kglobalacceld" not in actual
    assert "libksysguard" not in actual
    assert payload["stable_publication_authorized"] is False
    assert payload["base_stack"]["frameworks_pass_nodes"] == 65

builder = BUILDER.read_text()
for token in (
    "exactly one artifact ZIP",
    "artifact digest drift",
    "candidate version drift",
    "candidate architecture drift",
    "candidate source drift",
    "candidate binary set mismatch",
    "Checksums-Sha256",
    "render_binary_packages",
    "render_sources",
    "render_release",
    "SOURCE_DATE_EPOCH",
    "retained artifact digest drift",
    "Packages.gz",
    "Sources.gz",
    "InRelease",
    "Release.gpg",
    "signed proposed repositories require --signing-key",
    "--signed-certification",
    "signed certification requires --signing-key",
    '"certification_mode": certification_mode',
    '"activation_eligible": signing is not None and not args.signed_certification',
    '"stable_publication_authorized": False',
):
    assert token in builder, f"proposed builder missing contract: {token}"
for forbidden in ("apt-ftparchive", "trusted=yes", "allow-unauthenticated"):
    assert forbidden not in builder, f"unsafe proposed repository behavior: {forbidden}"

for token in (
    'raw.split(":", 1)',
    'gzip.GzipFile(fileobj=raw, mode="wb", mtime=0)',
):
    assert token in builder, f"proposed builder misses reproducible/parser contract: {token}"

builder_spec = importlib.util.spec_from_file_location(
    "supralinux_proposed_builder_test", BUILDER
)
builder_module = importlib.util.module_from_spec(builder_spec)
builder_spec.loader.exec_module(builder_module)

with tempfile.TemporaryDirectory() as td:
    fixture = Path(td)
    repo = fixture / "repo"
    source_dir = repo / "pool/main/f/fixture"
    source_dir.mkdir(parents=True)

    deb_root = fixture / "deb"
    (deb_root / "DEBIAN").mkdir(parents=True)
    (deb_root / "DEBIAN/control").write_text(
        "Package: fixture\n"
        "Source: fixture\n"
        "Version: 1.0\n"
        "Architecture: all\n"
        "Maintainer: Test <test@example.invalid>\n"
        "Description: SupraLINUX proposed repository fixture\n"
        " continuation line\n"
    )
    deb = repo / "pool/main/fixture_1.0_all.deb"
    subprocess.run(
        [
            "dpkg-deb",
            "--root-owner-group",
            "--build",
            str(deb_root),
            str(deb),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    orig = source_dir / "fixture_1.0.orig.tar.xz"
    debian_tar = source_dir / "fixture_1.0-1.debian.tar.xz"
    orig.write_bytes(b"fixture-orig")
    debian_tar.write_bytes(b"fixture-debian")
    dsc = source_dir / "fixture_1.0-1.dsc"
    dsc.write_text(
        "Format: 3.0 (quilt)\n"
        "Source: fixture\n"
        "Binary: fixture\n"
        "Architecture: all\n"
        "Version: 1.0\n"
        "Maintainer: Test <test@example.invalid>\n"
        "Checksums-Sha256:\n"
        f" {builder_module.sha256(orig)} {orig.stat().st_size} {orig.name}\n"
        f" {builder_module.sha256(debian_tar)} {debian_tar.stat().st_size} {debian_tar.name}\n"
    )

    checksum_entries = builder_module.dsc_sha256_entries(
        builder_module.dsc_fields(dsc), "fixture"
    )
    assert checksum_entries == [
        (builder_module.sha256(orig), str(orig.stat().st_size), orig.name),
        (
            builder_module.sha256(debian_tar),
            str(debian_tar.stat().st_size),
            debian_tar.name,
        ),
    ]

    packages_path, release_path = builder_module.build_indices(
        repo, "resolute-supralinux-proposed"
    )
    sources_path = (
        repo
        / "dists/resolute-supralinux-proposed/main/source/Sources"
    )
    packages_text = packages_path.read_text()
    sources_text = sources_path.read_text()
    release_text = release_path.read_text()

    assert "Package: fixture" in packages_text
    assert "Filename: pool/main/fixture_1.0_all.deb" in packages_text
    assert f"SHA256: {builder_module.sha256(deb)}" in packages_text
    assert "Package: fixture" in sources_text
    assert "Directory: pool/main/f/fixture" in sources_text
    assert "fixture_1.0-1.dsc" in sources_text
    assert "SHA256:" in release_text
    assert "main/binary-amd64/Packages" in release_text
    assert "main/source/Sources" in release_text
    assert "Date: " in release_text
    assert gzip.decompress(
        (packages_path.parent / "Packages.gz").read_bytes()
    ).decode() == packages_text
    assert gzip.decompress(
        (sources_path.parent / "Sources.gz").read_bytes()
    ).decode() == sources_text

    first = (
        builder_module.sha256(packages_path),
        builder_module.sha256(sources_path),
        builder_module.sha256(release_path),
    )
    builder_module.build_indices(repo, "resolute-supralinux-proposed")
    second = (
        builder_module.sha256(packages_path),
        builder_module.sha256(sources_path),
        builder_module.sha256(release_path),
    )
    assert second == first

promoter = PROMOTER.read_text()
for token in (
    "apt_solvability",
    "clean_install",
    "upgrade_from_ubuntu",
    "dependency_closure",
    "abi_and_plugins",
    "representative_apps",
    "wayland_session",
    "integration_image",
    '"promotion_target": "campaign-milestone"',
    '"stable_publication_authorized": False',
    '"stable_publication_requires_explicit_confirmation": True',
):
    assert token in promoter, f"promotion evaluator missing gate: {token}"

config = json.loads(CONFIG.read_text())
assert config["state"] == "prepared-inactive"
assert config["active"] is False
assert config["current_plasma_campaign_unchanged"] is True
assert config["repository_policy"]["signed_before_activation"] is True
assert config["promotion"]["proposed_to_stable"] == "never automatic"

print(
    "SupraLINUX-proposed contract: PASS; "
    f"eligible_plasma_candidates={len(expected)}"
)
