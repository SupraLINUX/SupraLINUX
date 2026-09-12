#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / ".work/tier1-reference"
SIGNING_SOURCE = ROOT / "packages/kde/threadweaver/debian/upstream/signing-key.asc"

assert (REF / "snapshot.json").is_file()
assert hashlib.sha256((REF / "snapshot.json").read_bytes()).hexdigest() == "f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345"
assert SIGNING_SOURCE.is_file()
assert hashlib.sha256(SIGNING_SOURCE.read_bytes()).hexdigest() == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d"

NODES = {
    "ktexttemplate": {
        "source_package": "kf6-ktexttemplate",
        "source_sha256": "c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
        "root_cmake_blob": "e68c80cc6106c87e321d23729f882052ab386972",
        "runtime": "libkf6texttemplate6",
        "dev": "libkf6texttemplate-dev",
        "doc": "libkf6texttemplate-doc",
        "soname": "libKF6TextTemplate.so.6",
        "cmake_package": "KF6TextTemplate",
        "cmake_target": "KF6::TextTemplate",
        "symbols_file": "libkf6texttemplate6.symbols",
        "symbols_sha256": "552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273",
        "copyright_sha256": "b7b88bf2a8f3f4d19fb85b0d00d1464430a4f97a1949616a16a5a956c6c97109",
        "build_depends": [
            "debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper",
            "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)",
            "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)",
        ],
        "contracts": [
            {"name": "libkf6texttemplate-dev", "architecture": "amd64", "multi_arch": None},
            {"name": "libkf6texttemplate-doc", "architecture": "all", "multi_arch": "foreign"},
            {"name": "libkf6texttemplate6", "architecture": "amd64", "multi_arch": "same"},
        ],
        "test_command": "dh_auto_test",
        "consumer": """#include <KTextTemplate/Engine>\n\nint main()\n{\n    KTextTemplate::Engine engine;\n    engine.setSmartTrimEnabled(true);\n    return engine.smartTrimEnabled() ? 0 : 1;\n}\n""",
    },
    "karchive": {
        "source_package": "kf6-karchive",
        "source_sha256": "4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
        "root_cmake_blob": "6f86222fb967c7f3e29c15ecef40bf355d8004d0",
        "runtime": "libkf6archive6",
        "dev": "libkf6archive-dev",
        "doc": "libkf6archive-doc",
        "soname": "libKF6Archive.so.6",
        "cmake_package": "KF6Archive",
        "cmake_target": "KF6::Archive",
        "symbols_file": "libkf6archive6.symbols",
        "symbols_sha256": "acd4b767ad9cc821345a973e09c1e42c63d45fc3eef45197a35d84475c83878e",
        "copyright_sha256": "c82d4cf65cdfb5255a04d9e842edc6df47aece48318fd4de6c7c9a61660006ff",
        "build_depends": [
            "debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper",
            "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)",
            "libbz2-dev", "liblzma-dev", "libssl-dev", "libzstd-dev", "pkgconf",
            "qt6-base-dev (>= 6.9.0~)", "zlib1g-dev", "zstd",
        ],
        "contracts": [
            {"name": "libkf6archive-data", "architecture": "all", "multi_arch": "foreign"},
            {"name": "libkf6archive-dev", "architecture": "amd64", "multi_arch": None},
            {"name": "libkf6archive-doc", "architecture": "all", "multi_arch": "foreign"},
            {"name": "libkf6archive6", "architecture": "amd64", "multi_arch": "same"},
        ],
        "test_command": "dh_auto_test",
        "consumer": """#include <KArchive/KZip>\n#include <QString>\n\nint main()\n{\n    KZip archive(QStringLiteral(\"/tmp/supralinux-karchive-consumer.zip\"));\n    archive.setCompression(KZip::NoCompression);\n    return archive.compression() == KZip::NoCompression ? 0 : 1;\n}\n""",
    },
    "kholidays": {
        "source_package": "kf6-kholidays",
        "source_sha256": "02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
        "root_cmake_blob": "ee43159b9e7259c8c4cefe0db38e2ca715b73ad9",
        "runtime": "libkf6holidays6",
        "dev": "libkf6holidays-dev",
        "doc": "libkf6holidays-doc",
        "soname": "libKF6Holidays.so.6",
        "cmake_package": "KF6Holidays",
        "cmake_target": "KF6::Holidays",
        "symbols_file": "libkf6holidays6.symbols",
        "symbols_sha256": "b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd",
        "copyright_sha256": "c9b4c8797fc5a93733224a2ed442a3de75b3bdb5ef24dd8bdf5abb48d34a1e73",
        "build_depends": [
            "debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper",
            "dh-sequence-qmldeps", "bison (>= 2:3.3.2~)", "cmake (>= 3.29~)",
            "extra-cmake-modules (>= 6.30.0~)", "flex", "qt6-base-dev (>= 6.9.0~)",
            "qt6-declarative-dev (>= 6.9.0~)",
        ],
        "contracts": [
            {"name": "libkf6holidays-data", "architecture": "all", "multi_arch": "foreign"},
            {"name": "libkf6holidays-dev", "architecture": "amd64", "multi_arch": "same"},
            {"name": "libkf6holidays-doc", "architecture": "all", "multi_arch": "foreign"},
            {"name": "libkf6holidays6", "architecture": "amd64", "multi_arch": "same"},
            {"name": "qml6-module-org-kde-kholidays", "architecture": "amd64", "multi_arch": "same"},
        ],
        "test_command": "dh_auto_test --no-parallel",
        "consumer": """#include <KHolidays/LunarPhase>\n#include <QDate>\n\nint main()\n{\n    const auto phase = KHolidays::LunarPhase::phaseAtDate(QDate(2026, 1, 1));\n    (void)phase;\n    return 0;\n}\n""",
    },
}


def parse_paragraph(text: str):
    fields: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")):
            if not fields:
                raise ValueError("orphan continuation")
            fields[-1][1].append(line)
        else:
            if ":" not in line:
                raise ValueError(f"invalid field line: {line!r}")
            name = line.split(":", 1)[0]
            fields.append((name, [line]))
    return fields


def render_paragraph(fields):
    return "\n".join(line for _, lines in fields for line in lines)


def make_control(node: str, meta: dict) -> str:
    source = (REF / "trees/ubuntu" / node / "debian/control").read_text(encoding="utf-8")
    paragraphs = source.strip().split("\n\n")
    first = parse_paragraph(paragraphs[0])
    new_fields = []
    for name, lines in first:
        if name in {"Maintainer", "XSBC-Original-Maintainer", "Uploaders", "Build-Depends", "Standards-Version", "Vcs-Git", "Vcs-Browser"}:
            continue
        new_fields.append((name, lines))
        if name == "Priority":
            new_fields.append(("Maintainer", ["Maintainer: SupraLINUX Project <packages@supralinux.invalid>"]))
            deps = meta["build_depends"]
            dep_lines = [f"Build-Depends: {deps[0]},"]
            dep_lines.extend(f"               {dep}," for dep in deps[1:])
            new_fields.append(("Build-Depends", dep_lines))
    # Standards-Version belongs before Homepage in Debian control style.
    idx = next(i for i, (name, _) in enumerate(new_fields) if name == "Homepage")
    new_fields.insert(idx, ("Standards-Version", ["Standards-Version: 4.7.3"]))
    paragraphs[0] = render_paragraph(new_fields)
    rest = "\n\n".join(paragraphs[1:])
    rest = rest.replace("6.8.0+dfsg~", "6.9.0~").replace("6.8.0~", "6.9.0~")
    return paragraphs[0] + "\n\n" + rest + "\n"


for node, meta in NODES.items():
    pkg = ROOT / "packages/kde" / node
    if pkg.exists():
        shutil.rmtree(pkg)
    deb = pkg / "debian"
    (deb / "source").mkdir(parents=True)
    (deb / "upstream").mkdir(parents=True)
    (pkg / "consumer").mkdir(parents=True)
    uref = REF / "trees/ubuntu" / node / "debian"
    dref = REF / "trees/debian" / node / "debian"
    assert uref.is_dir() and dref.is_dir()
    for src in sorted(uref.glob("*.install")):
        shutil.copy2(src, deb / src.name)
    shutil.copy2(SIGNING_SOURCE, deb / "upstream/signing-key.asc")
    (deb / "control").write_text(make_control(node, meta), encoding="utf-8")
    (deb / "source/format").write_text("3.0 (quilt)\n", encoding="utf-8")
    (deb / "watch").write_text(
        "Version: 5\n"
        "Source: https://download.kde.org/stable/frameworks/@ANY_VERSION@/\n"
        f"Matching-Pattern: {node}-@ANY_VERSION@@ARCHIVE_EXT@\n"
        "Pgp-Mode: auto\n",
        encoding="utf-8",
    )
    rules = textwrap.dedent(f"""\
        #!/usr/bin/make -f
        export DEB_BUILD_MAINT_OPTIONS = hardening=+all{" optimize=+lto" if node == "kholidays" else ""}

        %:
        \tdh $@

        override_dh_auto_configure:
        \tdh_auto_configure -- -DBUILD_TESTING=ON

        override_dh_auto_test:
        \t{meta['test_command']}
        """)
    (deb / "rules").write_text(rules, encoding="utf-8")
    (deb / "rules").chmod(0o755)
    (deb / "README.source").write_text(textwrap.dedent(f"""\
        # SupraLINUX {node} packaging

        KDE Frameworks 6.30.0 is the source/build authority. Ubuntu Resolute and Debian sid
        packaging trees are compatibility references only.

        The full symbols file is intentionally not duplicated in Git. The Batch 2 hosted
        runner verifies and injects the exact Debian 6.28 baseline from workflow run
        34708030450 / artifact 10301938362 before dpkg-source -b. Debian is selected for
        the symbols baseline because it is closer to KDE 6.30; Ubuntu remains the direct
        binary-compatibility target. Any 6.30 ABI delta must be reviewed from a real build.

        QDoc targets generated through ECMGenerateQDoc are not part of the default build.
        The established documentation binary package name is retained as a compatibility
        stub until SupraLINUX defines a common Frameworks QDoc policy. Upstream autotests
        remain enabled.
        """), encoding="utf-8")
    (deb / "copyright.reference").write_text(
        "# Debian sid packaging copyright metadata retained in generic Tier 1 packaging-tree artifact.\n"
        "workflow_run=34708030450\nartifact_id=10301938362\n"
        f"node={node}\npath=trees/debian/{node}/debian/copyright\nsha256={meta['copyright_sha256']}\n",
        encoding="utf-8",
    )
    (deb / f"{meta['symbols_file']}.reference").write_text(
        "# Debian sid symbols baseline retained in generic Tier 1 packaging-tree artifact.\n"
        "workflow_run=34708030450\nartifact_id=10301938362\nprovider=debian\nreference_version=6.28.0\n"
        f"node={node}\npath=trees/debian/{node}/debian/{meta['symbols_file']}\nsha256={meta['symbols_sha256']}\n",
        encoding="utf-8",
    )
    (deb / "changelog").write_text(textwrap.dedent(f"""\
        {meta['source_package']} (6.30.0-0supralinux1) resolute; urgency=medium

          * Package KDE Frameworks {node} 6.30.0 from KDE upstream stable.
          * Preserve Debian-family binary package names and Multi-Arch contracts as
            compatibility inputs while selecting dependencies from KDE 6.30 requirements.
          * Build against retained SupraLINUX ECM 6.30 and KDE-selected Qt >= 6.9.
          * Keep KDE upstream autotests enabled and keep QDoc outside the default build.
          * Use the retained Debian 6.28 symbols tree as the closest technical ABI baseline.

         -- SupraLINUX Project <packages@supralinux.invalid>  Sat, 12 Sep 2026 18:00:00 -0300
        """), encoding="utf-8")
    (pkg / "consumer/CMakeLists.txt").write_text(textwrap.dedent(f"""\
        cmake_minimum_required(VERSION 3.29)
        project(SupraLINUX{meta['cmake_package']}Consumer LANGUAGES CXX)
        find_package({meta['cmake_package']} 6.30.0 REQUIRED CONFIG)
        add_executable({node}-consumer main.cpp)
        target_link_libraries({node}-consumer PRIVATE {meta['cmake_target']})
        """), encoding="utf-8")
    (pkg / "consumer/main.cpp").write_text(meta["consumer"], encoding="utf-8")

campaign = {
    "schema": 1,
    "as_of": "2026-09-12",
    "frameworks_series": "6.30.0",
    "authority": "kde-upstream",
    "provider_platform": "ubuntu-resolute",
    "batch": "tier1-batch-2",
    "state": "prepared-pending-build",
    "canonical_state_role": "batch-package-attempt-ledger",
    "selected_nodes": list(NODES),
    "shared_predecessors": {
        "extra_cmake_modules": {
            "state": "PASS", "version": "6.30.0-0supralinux3", "workflow_run": 34694951158,
            "artifact_id": 10298635300, "deb_sha256": "ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f",
        },
        "packaging_trees": {
            "status": "PASS", "workflow_run": 34708030450, "artifact_id": 10301938362,
            "artifact_sha256": "6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6",
            "snapshot_json_sha256": "f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345",
        },
    },
    "shared_packaging_inputs": {
        "signing_key": {
            "path": "debian/upstream/signing-key.asc",
            "sha256": "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d",
            "source": "retained-debian-packaging-reference",
        }
    },
    "nodes": {},
}
for node, meta in NODES.items():
    campaign["nodes"][node] = {
        "state": "prepared-pending-build",
        "last_result": None,
        "downstream_eligible": False,
        "upstream_version": "6.30.0",
        "source_package": meta["source_package"],
        "source_sha256": meta["source_sha256"],
        "root_cmake_blob": meta["root_cmake_blob"],
        "source_url": f"https://download.kde.org/stable/frameworks/6.30/{node}-6.30.0.tar.xz",
        "runtime_package": meta["runtime"],
        "development_package": meta["dev"],
        "documentation_package": meta["doc"],
        "binary_contracts": meta["contracts"],
        "soname": meta["soname"],
        "cmake_package": meta["cmake_package"],
        "cmake_target": meta["cmake_target"],
        "consumer_run": "direct",
        "copyright": {"file": "copyright", "sha256": meta["copyright_sha256"], "reference": "debian-sid-6.28"},
        "package_version": "6.30.0-0supralinux1",
        "symbols": {
            "file": meta["symbols_file"], "sha256": meta["symbols_sha256"],
            "tree_provider": "debian", "reference_version": "6.28.0",
        },
        "evidence": [],
    }
(ROOT / "manifests/kde-tier1-package-campaign-batch2.json").write_text(json.dumps(campaign, indent=2) + "\n", encoding="utf-8")

old_runner = (ROOT / "scripts/run-kde-tier1-package-preflight.sh").read_text(encoding="utf-8")
needle = 'CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign.json"'
assert needle in old_runner
new_runner = old_runner.replace(needle, 'CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign-batch2.json"', 1)
runner_path = ROOT / "scripts/run-kde-tier1-package-batch2-preflight.sh"
runner_path.write_text(new_runner, encoding="utf-8")
runner_path.chmod(0o755)

old_scope = (ROOT / "scripts/kde-tier1-package-preflight-needed.sh").read_text(encoding="utf-8")
replacements = {
    "kcodecs|kdbusaddons|threadweaver": "ktexttemplate|karchive|kholidays",
    "manifests/kde-tier1-package-campaign.json": "manifests/kde-tier1-package-campaign-batch2.json",
    "scripts/run-kde-tier1-package-preflight.sh": "scripts/run-kde-tier1-package-batch2-preflight.sh",
    ".github/workflows/kde-tier1-package-preflight.yml": ".github/workflows/kde-tier1-package-batch2.yml",
    "scripts/kde-tier1-package-preflight-needed.sh": "scripts/kde-tier1-package-batch2-needed.sh",
}
new_scope = old_scope
for before, after in replacements.items():
    assert before in new_scope, before
    new_scope = new_scope.replace(before, after)
scope_path = ROOT / "scripts/kde-tier1-package-batch2-needed.sh"
scope_path.write_text(new_scope, encoding="utf-8")
scope_path.chmod(0o755)

workflow = """name: KDE Frameworks Tier 1 package batch 2

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:

permissions:
  contents: read
  actions: read

jobs:
  tier1-package:
    name: ${{ matrix.node }} 6.30 clean package preflight
    runs-on: ubuntu-26.04
    timeout-minutes: 60
    strategy:
      fail-fast: false
      max-parallel: 3
      matrix:
        node:
          - ktexttemplate
          - karchive
          - kholidays

    steps:
      - name: Checkout
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          fetch-depth: 0

      - name: Determine whether this event delta affects this Tier 1 node
        id: scope
        shell: bash
        run: |
          set -euo pipefail
          run=true
          if [[ "${{ github.event_name }}" == "pull_request" ]]; then
            if [[ "${{ github.event.action }}" == "synchronize" ]]; then
              before="${{ github.event.before }}"
              after="${{ github.event.after }}"
            else
              before="${{ github.event.pull_request.base.sha }}"
              after="${{ github.event.pull_request.head.sha }}"
            fi
            if bash scripts/kde-tier1-package-batch2-needed.sh "${{ matrix.node }}" "${before}" "${after}"; then
              run=true
            else
              rc=$?
              if [[ "${rc}" -eq 1 ]]; then run=false; else exit "${rc}"; fi
            fi
          fi
          echo "run=${run}" >> "${GITHUB_OUTPUT}"

      - name: Download retained ECM PASS artifact
        if: steps.scope.outputs.run == 'true'
        uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c
        with:
          artifact-ids: '10298635300'
          github-token: ${{ github.token }}
          repository: SupraLINUX/SupraLINUX
          run-id: '34694951158'
          path: .work/retained-ecm

      - name: Download retained Tier 1 packaging-tree artifact
        if: steps.scope.outputs.run == 'true'
        uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c
        with:
          artifact-ids: '10301938362'
          github-token: ${{ github.token }}
          repository: SupraLINUX/SupraLINUX
          run-id: '34708030450'
          path: .work/retained-tier1-reference

      - name: Build and validate KDE Framework package
        if: steps.scope.outputs.run == 'true'
        env:
          ECM_ARTIFACT_DIR: ${{ github.workspace }}/.work/retained-ecm
          TIER1_REFERENCE_DIR: ${{ github.workspace }}/.work/retained-tier1-reference
        run: bash scripts/run-kde-tier1-package-batch2-preflight.sh "${{ matrix.node }}"

      - name: Upload per-node package evidence
        if: steps.scope.outputs.run == 'true' && always()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
        with:
          name: kde-tier1-batch2-${{ matrix.node }}-package-${{ github.event.pull_request.head.sha || github.sha }}
          path: evidence/kde-tier1-package-preflight/${{ matrix.node }}/
          if-no-files-found: error
          retention-days: 90

      - name: Report intentionally skipped node
        if: steps.scope.outputs.run != 'true'
        run: echo "${{ matrix.node }} Batch 2 package preflight intentionally skipped; event delta does not affect this node."
"""
(ROOT / ".github/workflows/kde-tier1-package-batch2.yml").write_text(workflow, encoding="utf-8")

validator = r'''#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch2.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch2.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch2-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch2-needed.sh"
DOC = ROOT / "docs/kde-tier1-package-batch2.md"
EXPECTED = {
    "ktexttemplate": {"source":"c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493","root":"e68c80cc6106c87e321d23729f882052ab386972","symbols":"552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273","copyright":"b7b88bf2a8f3f4d19fb85b0d00d1464430a4f97a1949616a16a5a956c6c97109","runtime":"libkf6texttemplate6","soname":"libKF6TextTemplate.so.6","contracts":[("libkf6texttemplate-dev","amd64",None),("libkf6texttemplate-doc","all","foreign"),("libkf6texttemplate6","amd64","same")],"build":["qt6-base-dev (>= 6.9.0~)","qt6-declarative-dev (>= 6.9.0~)"]},
    "karchive": {"source":"4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2","root":"6f86222fb967c7f3e29c15ecef40bf355d8004d0","symbols":"acd4b767ad9cc821345a973e09c1e42c63d45fc3eef45197a35d84475c83878e","copyright":"c82d4cf65cdfb5255a04d9e842edc6df47aece48318fd4de6c7c9a61660006ff","runtime":"libkf6archive6","soname":"libKF6Archive.so.6","contracts":[("libkf6archive-data","all","foreign"),("libkf6archive-dev","amd64",None),("libkf6archive-doc","all","foreign"),("libkf6archive6","amd64","same")],"build":["libbz2-dev","liblzma-dev","libssl-dev","libzstd-dev","pkgconf","qt6-base-dev (>= 6.9.0~)","zlib1g-dev","zstd"]},
    "kholidays": {"source":"02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b","root":"ee43159b9e7259c8c4cefe0db38e2ca715b73ad9","symbols":"b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd","copyright":"c9b4c8797fc5a93733224a2ed442a3de75b3bdb5ef24dd8bdf5abb48d34a1e73","runtime":"libkf6holidays6","soname":"libKF6Holidays.so.6","contracts":[("libkf6holidays-data","all","foreign"),("libkf6holidays-dev","amd64","same"),("libkf6holidays-doc","all","foreign"),("libkf6holidays6","amd64","same"),("qml6-module-org-kde-kholidays","amd64","same")],"build":["dh-sequence-qmldeps","bison (>= 2:3.3.2~)","flex","qt6-base-dev (>= 6.9.0~)","qt6-declarative-dev (>= 6.9.0~)"]},
}
errors=[]
def req(value, message):
    if not value: errors.append(message)
def load(path): return json.loads(path.read_text(encoding="utf-8"))

campaign = load(CAMPAIGN)
tier1 = load(TIER1)
req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-2", "batch id")
req(campaign.get("state") == "prepared-pending-build", "batch must remain prepared until real attempts")
req(campaign.get("selected_nodes") == ["ktexttemplate", "karchive", "kholidays"], "selected nodes")
req(set(campaign.get("nodes", {})) == set(EXPECTED), "campaign node set")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_predecessors"]["packaging_trees"]["artifact_id"] == 10301938362, "tree artifact")
req(campaign["shared_packaging_inputs"]["signing_key"]["sha256"] == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", "signing key pin")
tier = {item["id"]: item for item in tier1["nodes"]}
for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "prepared-pending-build", f"{node}: campaign state")
    req(data["last_result"] is None and data["downstream_eligible"] is False, f"{node}: no invented result")
    req(data["package_version"] == "6.30.0-0supralinux1", f"{node}: revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["root_cmake_blob"] == expected["root"], f"{node}: CMake pin")
    req(data["runtime_package"] == expected["runtime"] and data["soname"] == expected["soname"], f"{node}: ABI identity")
    req(data["symbols"]["sha256"] == expected["symbols"] and data["symbols"]["tree_provider"] == "debian" and data["symbols"]["reference_version"] == "6.28.0", f"{node}: symbols baseline")
    req(data["copyright"]["sha256"] == expected["copyright"], f"{node}: copyright hash")
    req([(x["name"], x["architecture"], x["multi_arch"]) for x in data["binary_contracts"]] == expected["contracts"], f"{node}: binary contracts")
    req(data["evidence"] == [], f"{node}: evidence must be empty before attempt")
    req(tier[node]["state"] == "pending" and tier[node]["packaging"] == {"state":"pending"}, f"{node}: canonical Tier1 must remain pending")
    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("BUILD_QCH" not in rules, f"{node}: stale BUILD_QCH forbidden")
    req("-DBUILD_TESTING=ON" in rules and "dh_auto_test" in rules, f"{node}: upstream tests must run")
    req("Disable auto tests" not in rules, f"{node}: tests may not be disabled")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority doc")
    req((deb / "source/format").read_text(encoding="utf-8") == "3.0 (quilt)\n", f"{node}: source format")
    key = deb / "upstream/signing-key.asc"
    req(hashlib.sha256(key.read_bytes()).hexdigest() == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req((ROOT / "packages/kde" / node / "consumer/CMakeLists.txt").is_file() and (ROOT / "packages/kde" / node / "consumer/main.cpp").is_file(), f"{node}: consumer")

runner = RUNNER.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
req("kde-tier1-package-campaign-batch2.json" in runner and "kde-tier1-package-campaign.json\"" not in runner, "Batch2 runner must be isolated from Batch1 ledger")
for token in ["ktexttemplate|karchive|kholidays", "kde-tier1-package-campaign-batch2.json", "run-kde-tier1-package-batch2-preflight.sh", "kde-tier1-package-batch2.yml"]:
    req(token in scope, f"scope missing {token}")
for token in ["- ktexttemplate", "- karchive", "- kholidays", "fail-fast: false", "max-parallel: 3", "run-kde-tier1-package-batch2-preflight.sh"]:
    req(token in workflow, f"workflow missing {token}")
for token in ["KTextTemplate", "KArchive", "KHolidays", "Debian 6.28", "Ubuntu Resolute", "BUILD_TESTING", "QDoc"]:
    req(token in doc, f"doc missing {token}")
if errors:
    for error in errors: print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 1 Batch 2 preparation validation: PASS")
print("Prepared nodes: ktexttemplate, karchive, kholidays")
print("Canonical Tier 1 state unchanged: 4 PASS, 25 pending, 0 FAIL, 0 BLOCKED")
'''
validator_path = ROOT / "scripts/validate_kde_tier1_package_batch2.py"
validator_path.write_text(validator, encoding="utf-8")
validator_path.chmod(0o755)

doc = '''# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **prepared; no package result claimed yet**

Batch 2 contains three independent Tier 1 nodes: **KTextTemplate**, **KArchive** and **KHolidays**. KDE upstream 6.30.0 remains the source/build authority. Ubuntu Resolute is the direct compatibility/provider target; Debian sid packaging is a technical reference only.

## Selection rationale

The three nodes depend only on the already-PASS ECM root inside KDE Frameworks and therefore can be attempted in parallel. They deliberately exercise different integration profiles without introducing a Framework-to-Framework dependency: KTextTemplate exercises Qt Core plus its upstream optional QML integration, KArchive exercises KDE's default compression backends, and KHolidays exercises required Qt QML plus Flex/Bison parser generation.

KItemModels was not selected for this batch because its build/test profile adds QML test modules and Xvfb. It remains pending and can be handled in a later independent batch.

## Upstream 6.30 requirements retained

- KTextTemplate: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 required; Qt QML is optional upstream and intentionally available in the SupraLINUX build so the established plugin/runtime contract remains present.
- KArchive: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 plus the upstream-default ZLIB, BZip2, LibLZMA, OpenSSL and LibZstd backends. No default compression backend is disabled.
- KHolidays: CMake >= 3.29, ECM 6.30, Qt Core+QML >= 6.9, Flex and Bison >= 3.3.2.

`BUILD_TESTING=ON` is explicit for all three. KHolidays retains serialized `dh_auto_test --no-parallel` from the technical packaging reference; this changes scheduling only and does not suppress tests. The Ubuntu/Debian `BUILD_QCH=ON` flag is not copied because Frameworks 6.30 uses explicit ECMGenerateQDoc targets; QDoc remains a later common policy phase.

## ABI and compatibility inputs

Binary names, Architecture and Multi-Arch contracts follow the retained Ubuntu Resolute binary-contract snapshot. Symbols use the retained **Debian 6.28** trees because they are closer to KDE 6.30 than Ubuntu 6.24. This does not make Debian an authority: a real 6.30 build must prove the ABI with `dpkg-gensymbols`; any new/missing symbol becomes real evidence to review, not something pre-filled here.

Reference source: workflow run `34708030450`, artifact `10301938362`. ECM predecessor: `extra-cmake-modules 6.30.0-0supralinux3`, artifact `10298635300`.

## State semantics

Preparation does not promote the canonical Tier 1 DAG. Until the hosted clean-package jobs actually run, KTextTemplate, KArchive and KHolidays remain `pending`. A real own-cause failure becomes FAIL; a node is BLOCKED only when an actual failed predecessor prevents its attempt. Independent jobs continue regardless of another Batch 2 result.
'''
(ROOT / "docs/kde-tier1-package-batch2.md").write_text(doc, encoding="utf-8")

status = ROOT / "docs/status/2026-09-12.md"
text = status.read_text(encoding="utf-8")
old = "## Next gate\n\nClose Batch 1 with Repository Policy and a no-rebuild scope proof, then prepare Batch 2 from the remaining 25 independent Tier 1 nodes. Hosted package PASS still does not replace the authoritative KVM/JIT release lane."
new = '''## Batch 1 closure and Batch 2 preparation

Commit `c87d879316766f8d02c4782fbe0942d6e8707dfe` closed Batch 1. Repository Policy and all other workflows on that commit PASSed; the KCodecs, KDBusAddons and ThreadWeaver package jobs proved the corrected scope by skipping 3/3 builds, artifact downloads and uploads.

Batch 2 is prepared for KTextTemplate, KArchive and KHolidays. Preparation does **not** change canonical package state: the project remains 4 PASS, 25 pending, 0 current FAIL, 0 BLOCKED until real clean-package attempts produce evidence.

## Next gate

Run the three Batch 2 clean hosted package attempts in parallel, retain each result independently, remediate own-cause FAILs incrementally, then synchronize canonical Tier 1/DAG documentation only from real evidence. Hosted PASS still does not replace the authoritative KVM/JIT release lane.'''
assert old in text
status.write_text(text.replace(old, new), encoding="utf-8")

tierdoc = ROOT / "docs/kde-tier1.md"
text = tierdoc.read_text(encoding="utf-8")
old = "## Next stage\n\nBatch 2 should prepare another group of independent low-dependency Tier 1 nodes from the remaining 25, preserving per-package binary contracts, symbols/ABI policy, optional features, tests and consumer smokes. Independent failures must not stop unrelated nodes."
new = '''## Batch 2 prepared

KTextTemplate, KArchive and KHolidays are the next independent package attempts. Their preparation lives in a separate Batch 2 campaign so the closed Batch 1 ledger and runner remain reproducible. Debian 6.28 symbols are used as the closer technical ABI baseline while Ubuntu Resolute remains the direct binary-compatibility target. KDE 6.30 upstream defaults and autotests remain enabled; stale distro `BUILD_QCH` settings are not inherited.

Canonical state is still **4 PASS / 25 pending / 0 FAIL / 0 BLOCKED** until these jobs actually attempt their packages.'''
assert old in text
tierdoc.write_text(text.replace(old, new), encoding="utf-8")

policy = ROOT / ".github/workflows/repository-policy.yml"
text = policy.read_text(encoding="utf-8")
marker = "      - name: Validate KDE Tier 1 batch 1 preparation\n        run: python3 scripts/validate_kde_tier1_package_batch1.py\n"
insert = marker + "\n      - name: Validate KDE Tier 1 batch 2 preparation\n        run: python3 scripts/validate_kde_tier1_package_batch2.py\n"
assert marker in text and "validate_kde_tier1_package_batch2.py" not in text
policy.write_text(text.replace(marker, insert), encoding="utf-8")

print("Batch 2 generation complete")
