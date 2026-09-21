#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "manifests/kde-tier2-package-contracts.json"
TIER2 = ROOT / "manifests/kde-frameworks-tier2.json"
CI_MAINTAINER = "SupraLINUX Build System <build@supralinux.invalid>"
VCS_GIT = "https://github.com/SupraLINUX/SupraLINUX.git -b architecture/bootstrap-v1"
VCS_BROWSER = "https://github.com/SupraLINUX/SupraLINUX/tree/architecture/bootstrap-v1"
PYTHON_BUILD_DEPS = [
    "dh-sequence-python3",
    "libpyside6-dev",
    "libshiboken6-dev",
    "python3-build",
    "python3-dev",
    "python3-setuptools",
    "python3-wheel",
]


def load(path: Path):
    return json.loads(path.read_text())


def spans(lines: list[str]):
    result = {}
    starts = []
    for i, line in enumerate(lines):
        if line and not line[0].isspace() and ":" in line:
            starts.append((i, line.split(":", 1)[0]))
    for pos, (start, name) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        result[name] = (start, end)
    return result


def field_value(lines: list[str], name: str):
    s = spans(lines).get(name)
    if not s:
        return None
    start, end = s
    first = lines[start].split(":", 1)[1].strip()
    rest = [line.strip() for line in lines[start + 1 : end]]
    return " ".join([first, *rest]).strip()


def set_field(lines: list[str], name: str, value: str):
    mapping = spans(lines)
    replacement = [f"{name}: {value}"]
    if name in mapping:
        start, end = mapping[name]
        lines[start:end] = replacement
    else:
        lines.extend(replacement)


def remove_field(lines: list[str], name: str):
    mapping = spans(lines)
    if name in mapping:
        start, end = mapping[name]
        del lines[start:end]


def dependency_name(dep: str) -> str:
    return re.split(r"\s|\(", dep, maxsplit=1)[0]


def render_build_depends(lines: list[str], deps: list[str]):
    if not deps:
        raise SystemExit("Build-Depends cannot become empty")
    rendered = "Build-Depends: " + deps[0]
    if len(deps) > 1:
        rendered += ",\n" + "\n".join(
            "               " + dep + ("," if i < len(deps) - 1 else "")
            for i, dep in enumerate(deps[1:], start=1)
        )
    mapping = spans(lines)
    start, end = mapping["Build-Depends"]
    lines[start:end] = rendered.splitlines()


def remove_build_depends(lines: list[str], removals: list[str]):
    if not removals:
        return
    current = field_value(lines, "Build-Depends")
    if current is None:
        raise SystemExit("debian/control lacks Build-Depends")
    deps = [x.strip() for x in current.split(",") if x.strip()]
    names = {dependency_name(dep) for dep in deps}
    missing = sorted(set(removals) - names)
    if missing:
        raise SystemExit(f"technical reference missing expected removable Build-Depends: {missing}")
    removal_set = set(removals)
    kept = [dep for dep in deps if dependency_name(dep) not in removal_set]
    render_build_depends(lines, kept)


def set_build_depends(lines: list[str], additions: list[str]):
    current = field_value(lines, "Build-Depends")
    if current is None:
        raise SystemExit("debian/control lacks Build-Depends")
    deps = [x.strip() for x in current.split(",") if x.strip()]
    present_names = {dependency_name(dep) for dep in deps}
    for dep in additions:
        if dep not in present_names:
            deps.append(dep)
    render_build_depends(lines, deps)


def render_dependency_field(lines: list[str], name: str, deps: list[str]):
    if not deps:
        raise SystemExit(f"{name} cannot become empty")
    rendered = f"{name}: " + deps[0]
    if len(deps) > 1:
        indent = " " * (len(name) + 2)
        rendered += ",\n" + "\n".join(
            indent + dep + ("," if i < len(deps) - 1 else "")
            for i, dep in enumerate(deps[1:], start=1)
        )
    mapping = spans(lines)
    if name not in mapping:
        raise SystemExit(f"binary stanza lacks {name}")
    start, end = mapping[name]
    lines[start:end] = rendered.splitlines()


def remove_binary_depends(paragraphs: list[str], removals_by_package: dict[str, list[str]]):
    for package, removals in removals_by_package.items():
        matches = []
        for i, paragraph in enumerate(paragraphs[1:], start=1):
            lines = paragraph.splitlines()
            if field_value(lines, "Package") == package:
                matches.append((i, lines))
        if len(matches) != 1:
            raise SystemExit(f"expected exactly one binary stanza for {package}, found {len(matches)}")
        index, lines = matches[0]
        current = field_value(lines, "Depends")
        if current is None:
            raise SystemExit(f"{package}: technical reference lacks Depends")
        deps = [x.strip() for x in current.split(",") if x.strip()]
        names = {dependency_name(dep) for dep in deps}
        missing = sorted(set(removals) - names)
        if missing:
            raise SystemExit(f"{package}: technical reference missing expected removable Depends: {missing}")
        removal_set = set(removals)
        kept = [dep for dep in deps if dependency_name(dep) not in removal_set]
        render_dependency_field(lines, "Depends", kept)
        paragraphs[index] = "\n".join(lines)


def remove_install_entries(debian: Path, removals_by_file: dict[str, list[str]]):
    for filename, removals in removals_by_file.items():
        path = debian / filename
        if not path.exists():
            raise SystemExit(f"install-entry removal target missing: {path}")
        lines = path.read_text().splitlines()
        missing = [entry for entry in removals if entry not in lines]
        if missing:
            raise SystemExit(f"{filename}: technical reference missing expected removable install entries: {missing}")
        removal_set = set(removals)
        kept = [line for line in lines if line not in removal_set]
        if not any(line.strip() and not line.lstrip().startswith("#") for line in kept):
            raise SystemExit(f"{filename}: install-entry removal would empty package payload")
        path.write_text("\n".join(kept) + "\n")


def split_binary_packages(debian: Path, paragraphs: list[str], specs: list[dict]):
    for spec in specs:
        package = spec["package"]
        needle = spec["source_match_substring"]
        target_install = debian / f"{package}.install"
        if target_install.exists():
            raise SystemExit(f"{package}: split target install file already exists in technical reference")

        matches = []
        for path in sorted(debian.glob("*.install")):
            lines = path.read_text().splitlines()
            for index, line in enumerate(lines):
                if needle in line and line.strip() and not line.lstrip().startswith("#"):
                    matches.append((path, index, line))
        if len(matches) != 1:
            raise SystemExit(f"{package}: expected exactly one install entry containing {needle!r}, found {len(matches)}")

        source_path, index, entry = matches[0]
        lines = source_path.read_text().splitlines()
        del lines[index]
        if not any(line.strip() and not line.lstrip().startswith("#") for line in lines):
            raise SystemExit(f"{package}: split would empty source install file {source_path.name}")
        source_path.write_text("\n".join(lines) + "\n")
        target_install.write_text(entry + "\n")

        if any(field_value(paragraph.splitlines(), "Package") == package for paragraph in paragraphs[1:]):
            raise SystemExit(f"{package}: split package already exists in technical reference")

        stanza = [
            f"Package: {package}",
            f"Section: {spec.get('section', 'libs')}",
            f"Architecture: {spec.get('architecture', 'any')}",
        ]
        if spec.get("multi_arch"):
            stanza.append(f"Multi-Arch: {spec['multi_arch']}")
        deps = spec.get("depends", [])
        if deps:
            stanza.append("Depends: " + deps[0] + ("," if len(deps) > 1 else ""))
            for i, dep in enumerate(deps[1:], start=1):
                stanza.append("         " + dep + ("," if i < len(deps) - 1 else ""))
        stanza.extend([
            f"Description: {spec['description_short']}",
            f" {spec['description_long']}",
        ])
        paragraphs.append("\n".join(stanza))


def set_auto_test_override(path: Path, command: str | None):
    if not command:
        return
    lines = path.read_text().splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == "override_dh_auto_test:"]
    if len(starts) != 1:
        raise SystemExit(f"expected exactly one override_dh_auto_test block, found {len(starts)}")
    start = starts[0]
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith(("\t", " ")) or not line.strip():
            end += 1
            continue
        break
    lines[start:end] = ["override_dh_auto_test:", "\t" + command, ""]
    path.write_text("\n".join(lines).rstrip() + "\n")



def modify_control(path: Path, node: dict, debhelper_compat: dict, shiboken_provider: dict):
    text = path.read_text()
    reference_level = int(debhelper_compat["technical_reference_level"])
    selected_level = int(debhelper_compat["selected_level"])
    pattern = re.compile(rf"debhelper-compat\s*\(=\s*{reference_level}\s*\)")
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one debhelper-compat (= {reference_level}) in technical reference, "
            f"found {len(matches)}"
        )
    text = pattern.sub(f"debhelper-compat (= {selected_level})", text, count=1)
    paragraphs = re.split(r"\n\s*\n", text.strip())
    if not paragraphs:
        raise SystemExit("empty debian/control")
    source_lines = paragraphs[0].splitlines()
    original_maintainer = field_value(source_lines, "Maintainer")
    if not original_maintainer:
        raise SystemExit("debian/control lacks Maintainer")
    remove_field(source_lines, "Uploaders")
    set_field(source_lines, "Maintainer", CI_MAINTAINER)
    set_field(source_lines, "Vcs-Git", VCS_GIT)
    set_field(source_lines, "Vcs-Browser", VCS_BROWSER)
    # Add this last so no later source-field rewrite can consume it as part of
    # a preceding multi-line field span.
    set_field(source_lines, "XSBC-Original-Maintainer", original_maintainer)
    remove_build_depends(source_lines, node.get("build_depends_remove", []))

    python_module = node.get("python_module")
    if python_module:
        provider_packages = shiboken_provider.get("provider_packages", [])
        if not provider_packages:
            raise SystemExit("missing Shiboken Clang-discovery provider package closure")
        set_build_depends(source_lines, [*PYTHON_BUILD_DEPS, *provider_packages])

    paragraphs[0] = "\n".join(source_lines)
    remove_binary_depends(paragraphs, node.get("binary_depends_remove", {}))
    split_binary_packages(path.parent, paragraphs, node.get("binary_package_splits", []))
    if python_module:
        pkg = node["supralinux_additional_binary_packages"][0]
        runtime = node["python_runtime_package"]
        runtime_contract = node.get("python_runtime_contract", {})
        pyside_runtime_packages = runtime_contract.get("provider_packages", [])
        if not pyside_runtime_packages:
            raise SystemExit(f"{pkg}: missing PySide6 runtime provider contract")
        python_depends = [
            f"Depends: {runtime} (= " + "$" + "{binary:Version}),",
            *[f"         {dep}," for dep in pyside_runtime_packages],
            "         " + "$" + "{misc:Depends},",
            "         " + "$" + "{python3:Depends},",
            "         " + "$" + "{shlibs:Depends},",
        ]
        if any(re.search(rf"^Package:\s*{re.escape(pkg)}\s*$", p, re.M) for p in paragraphs[1:]):
            raise SystemExit(f"Python package already exists in technical reference: {pkg}")
        paragraphs.append(
            "\n".join(
                [
                    f"Package: {pkg}",
                    "Section: python",
                    "Architecture: any",
                    *python_depends,
                    f"Description: Python bindings for {python_module}",
                    f" Python 3 bindings generated by KDE upstream for {python_module}.",
                    " .",
                    " This package is provided by SupraLINUX because the upstream Linux",
                    " profile enables these bindings and the technical Debian reference",
                    " disables them.",
                ]
            )
        )
        install = path.parent / f"{pkg}.install"
        install.write_text(f"usr/lib/python3/dist-packages/{python_module}*.so\n")

    path.write_text("\n\n".join(paragraphs) + "\n")



def apply_symbols_adjustments(debian: Path, node: dict):
    for adjustment in node.get("symbols_adjustments", []):
        path = debian / adjustment["file"]
        if not path.exists():
            raise SystemExit(f"symbols adjustment target missing: {path}")
        symbol = adjustment["symbol"]
        version = adjustment["version"]
        tag = adjustment.get("tag")
        lines = path.read_text().splitlines()
        if any(symbol in line for line in lines):
            raise SystemExit(f"symbols baseline unexpectedly already contains reviewed symbol: {symbol}")
        rendered = f" ({tag}){symbol} {version}" if tag else f" {symbol} {version}"
        insert_at = len(lines)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "*", "lib")):
                continue
            token = stripped.split()[0]
            if token.startswith("(") and ")" in token:
                token = token.split(")", 1)[1]
            if token > symbol:
                insert_at = i
                break
        lines.insert(insert_at, rendered)
        path.write_text("\n".join(lines) + "\n")


def cmake_flags(profile: dict) -> list[str]:
    flags = []
    for key, value in profile.items():
        if key == "BUILD_QML_IF_PROVIDER_AVAILABLE":
            continue
        if not isinstance(value, bool):
            continue
        flags.append(f"-D{key}={'ON' if value else 'OFF'}")
    return flags


def modify_rules(path: Path, profile: dict):
    text = path.read_text()
    flags = cmake_flags(profile)
    for flag in flags:
        key = flag.split("=", 1)[0]
        text = re.sub(rf"{re.escape(key)}=(?:ON|OFF)", flag, text)

    missing = [flag for flag in flags if flag not in text]
    if missing:
        lines = text.splitlines()
        inserted = False
        for i, line in enumerate(lines):
            if re.match(r"^\s*dh_auto_configure\b", line):
                if " -- " in line:
                    lines[i] = line + " " + " ".join(missing)
                else:
                    lines[i] = line + " -- " + " ".join(missing)
                inserted = True
                break
        if not inserted:
            lines += ["", "override_dh_auto_configure:", "\tdh_auto_configure -- " + " ".join(missing)]
        text = "\n".join(lines) + "\n"

    path.write_text(text)


def prepend_changelog(path: Path, source_package: str, version: str, distribution: str):
    old = path.read_text()
    entry = (
        f"{source_package} ({version}) {distribution}; urgency=medium\n\n"
        "  * Materialize SupraLINUX packaging from KDE upstream source and the\n"
        "    pinned Debian packaging tree used only as a technical reference.\n"
        "  * Preserve upstream-selected Linux features.\n\n"
        f" -- {CI_MAINTAINER}  Sun, 20 Sep 2026 00:00:00 +0000\n\n"
    )
    path.write_text(entry + old)


def append_readme(path: Path):
    note = (
        "\n\n## SupraLINUX materialization\n\n"
        "This tree is generated from the authoritative KDE Frameworks 6.30.0 "
        "source plus a SHA-256-pinned Debian packaging tree used only as a "
        "technical reference. Debian/Ubuntu do not define the selected KDE "
        "feature profile. The CI maintainer address uses the reserved .invalid "
        "TLD and must be replaced by an approved SupraLINUX project contact "
        "before repository publication.\n"
    )
    if path.exists():
        text = path.read_text()
        if "## SupraLINUX materialization" not in text:
            path.write_text(text.rstrip() + note)
    else:
        path.write_text("# Source packaging notes" + note)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()

    contracts = load(CONTRACTS)
    tier2 = load(TIER2)
    if contracts.get("state") not in {"reference-capture-pass", "materialized"}:
        raise SystemExit("package-contract state is not materializable")
    if contracts.get("materialization", {}).get("status") not in {"pending-ci", "PASS"}:
        raise SystemExit("unsupported materialization state")
    if args.node not in contracts.get("selected_nodes", []):
        raise SystemExit(f"node not selected for materialization: {args.node}")

    node = contracts["nodes"][args.node]
    canonical = {n["id"]: n for n in tier2["nodes"]}[args.node]
    if canonical.get("source_sha256") != node.get("source_sha256"):
        raise SystemExit("source authority SHA drift")
    if canonical.get("planning", {}).get("readiness") not in {"package-contract-ready", "build-ready"}:
        raise SystemExit("node is not materialization/build ready")
    if canonical.get("planning", {}).get("package_contract") not in {"not-materialized", "materialized"}:
        raise SystemExit("node package-contract state is not compatible with materialization")

    root = Path(args.source_root)
    debian = root / "debian"
    for required in (debian / "control", debian / "rules", debian / "changelog", debian / "source" / "format"):
        if not required.exists():
            raise SystemExit(f"missing technical reference file: {required}")

    provider_adaptations = contracts.get("provider_adaptations", {}).get("ubuntu-resolute", {})
    debhelper_compat = provider_adaptations.get("debhelper_compat")
    changelog_distribution = provider_adaptations.get("changelog_distribution")
    shiboken_provider = provider_adaptations.get("shiboken_clang_discovery")
    if not debhelper_compat or not changelog_distribution or not shiboken_provider:
        raise SystemExit("missing Ubuntu Resolute packaging/provider adaptations")
    if any(x.get("kde_feature_effect") != "none" for x in (debhelper_compat, changelog_distribution, shiboken_provider)):
        raise SystemExit("provider adaptations must not alter the KDE feature profile")
    if node.get("python_module") and args.node not in shiboken_provider.get("applies_to", []):
        raise SystemExit("Python-binding node missing from Shiboken provider adaptation scope")
    distribution = changelog_distribution.get("selected")
    if distribution != "resolute":
        raise SystemExit("unexpected SupraLINUX changelog distribution")
    modify_control(debian / "control", node, debhelper_compat, shiboken_provider)
    remove_install_entries(debian, node.get("install_entries_remove", {}))
    apply_symbols_adjustments(debian, node)
    modify_rules(debian / "rules", node["selected_profile"])
    set_auto_test_override(debian / "rules", node.get("rules_auto_test_command"))
    prepend_changelog(debian / "changelog", node["source_package"], node["package_version_candidate"], distribution)
    append_readme(debian / "README.source")

    metadata = {
        "schema": 1,
        "node": args.node,
        "source_authority": "kde-upstream",
        "upstream_version": node["upstream_version"],
        "upstream_source_sha256": node["source_sha256"],
        "technical_reference": {
            "provider": "debian-sid",
            "version": node["technical_references"]["debian"]["version"],
            "debian_tar_sha256": node["technical_references"]["debian"]["debian_tar_sha256"],
        },
        "package_version": node["package_version_candidate"],
        "selected_profile": node["selected_profile"],
        "python_module": node.get("python_module"),
        "source_distribution": node.get("source_distribution", {"mode": "upstream-orig"}),
        "generated_maintainer": CI_MAINTAINER,
        "provider_adaptations": {
            "debhelper_compat": debhelper_compat,
            "changelog_distribution": changelog_distribution,
            **({"shiboken_clang_discovery": shiboken_provider} if node.get("python_module") else {}),
        },
        "python_runtime_contract": node.get("python_runtime_contract"),
        "symbols_adjustments": node.get("symbols_adjustments", []),
        "build_depends_remove": node.get("build_depends_remove", []),
        "binary_depends_remove": node.get("binary_depends_remove", {}),
        "install_entries_remove": node.get("install_entries_remove", {}),
        "binary_package_splits": node.get("binary_package_splits", []),
        "rules_auto_test_command": node.get("rules_auto_test_command"),
        "test_environment_adaptation": node.get("test_environment_adaptation"),
        "package_state_effect": "none",
    }
    (debian / "supralinux-materialization.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
