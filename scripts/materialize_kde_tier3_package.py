#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/kde-tier3-materialization.json"
CONTRACTS = ROOT / "manifests/kde-tier3-package-contracts.json"
CANONICAL = ROOT / "manifests/kde-frameworks-tier3.json"

STAGE = "initialization"
NODE = sys.argv[1] if len(sys.argv) == 2 else ""
WORK = ROOT / ".work/kde-tier3-materialization" / NODE
EVIDENCE = ROOT / "evidence/kde-tier3-materialization" / NODE


def run(args, *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    print("+", " ".join(str(x) for x in args), flush=True)
    return subprocess.run(
        [str(x) for x in args], cwd=cwd, check=True,
        text=capture, stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_record(root: Path) -> tuple[str, list[dict]]:
    rows: list[dict] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        st = path.lstat()
        mode = stat.S_IMODE(st.st_mode)
        if path.is_symlink():
            kind = "symlink"
            target = os.readlink(path)
            digest = hashlib.sha256(("symlink:" + target).encode()).hexdigest()
        elif path.is_file():
            kind = "file"
            target = None
            digest = sha256(path)
        elif path.is_dir():
            continue
        else:
            kind = "other"
            target = None
            digest = ""
        rows.append({"path": rel, "kind": kind, "mode": f"{mode:o}", "sha256": digest, "target": target})
    blob = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(blob).hexdigest(), rows


def paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text.strip("\n"))


def field_value(para: str, field: str) -> str | None:
    m = re.search(rf"(?mi)^{re.escape(field)}:\s*(.*(?:\n[ \t].*)*)", para)
    if not m:
        return None
    return " ".join(x.strip() for x in m.group(1).splitlines()).strip()


def set_field(para: str, field: str, value: str) -> str:
    pat = re.compile(rf"(?mi)^{re.escape(field)}:\s*.*(?:\n[ \t].*)*")
    repl = f"{field}: {value}"
    if pat.search(para):
        return pat.sub(repl, para, count=1)
    return para.rstrip() + "\n" + repl


def remove_field(para: str, field: str) -> str:
    pat = re.compile(rf"(?mi)^{re.escape(field)}:\s*.*(?:\n[ \t].*)*\n?")
    return pat.sub("", para, count=1).rstrip()


def package_para(parts: list[str], package: str) -> tuple[int, str]:
    for i, para in enumerate(parts):
        if field_value(para, "Package") == package:
            return i, para
    raise RuntimeError(f"binary package paragraph missing: {package}")


def split_relations(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def relation_name(rel: str) -> str:
    first = rel.split("|", 1)[0].strip()
    return re.split(r"\s|\(|\[|<", first, 1)[0]


def ensure_relation(para: str, field: str, relation: str) -> str:
    cur = split_relations(field_value(para, field))
    wanted = relation_name(relation)
    if not any(relation_name(x) == wanted for x in cur):
        cur.append(relation)
    return set_field(para, field, ", ".join(cur))


def remove_relation(para: str, field: str, package: str) -> str:
    cur = [x for x in split_relations(field_value(para, field)) if relation_name(x) != package]
    if cur:
        return set_field(para, field, ", ".join(cur))
    return remove_field(para, field)


def sanitize_test_suppression(rules: str) -> str:
    # Distribution reference policy may not globally disable upstream tests.
    rules = re.sub(r"(?m)^\s*(?:export\s+)?DEB_BUILD_OPTIONS\s*\+?=.*\bnocheck\b.*\n?", "", rules)
    lines = rules.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^override_dh_auto_test\s*:\s*$", line):
            j = i + 1
            block: list[str] = []
            while j < len(lines) and (lines[j].startswith(("\t", " ")) or not lines[j].strip() or lines[j].lstrip().startswith("#")):
                block.append(lines[j])
                j += 1
            meaningful = [x.strip() for x in block if x.strip() and not x.lstrip().startswith("#")]
            if not meaningful or (not any("dh_auto_test" in x for x in meaningful) and all(x in {":", "true", "@:", "@true"} for x in meaningful)):
                out.append(line)
                out.append("\tdh_auto_test")
                i = j
                continue
            if any("dh_auto_test" in x for x in meaningful):
                block = [re.sub(r"^(\s*)-dh_auto_test", r"\1dh_auto_test", x) for x in block]
                block = [re.sub(r"\s*\|\|\s*true\s*$", "", x) if "dh_auto_test" in x else x for x in block]
                out.append(line)
                out.extend(block)
                i = j
                continue
        out.append(line)
        i += 1
    return "\n".join(out).rstrip() + "\n"


def validate_test_policy(rules: str) -> None:
    lines = rules.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^override_dh_auto_test\s*:\s*$", line):
            j = i + 1
            block = []
            while j < len(lines) and (lines[j].startswith(("\t", " ")) or not lines[j].strip() or lines[j].lstrip().startswith("#")):
                block.append(lines[j]); j += 1
            meaningful = [x.strip() for x in block if x.strip() and not x.lstrip().startswith("#")]
            if not any("dh_auto_test" in x for x in meaningful):
                raise RuntimeError("override_dh_auto_test still suppresses upstream tests")
            if any("|| true" in x or x.lstrip().startswith("-dh_auto_test") for x in meaningful):
                raise RuntimeError("dh_auto_test failure suppression remains")
            return


def cmake_flags(rules: str, profile: dict) -> str:
    desired: dict[str, str] = {"BUILD_TESTING": "ON"}
    for key, value in profile.items():
        if isinstance(value, bool):
            desired[key] = "ON" if value else "OFF"

    # First normalize flags the reference already sets.
    missing: list[str] = []
    for key, value in desired.items():
        pat = re.compile(rf"-D{re.escape(key)}=(?:ON|OFF|TRUE|FALSE|0|1)", re.I)
        if pat.search(rules):
            rules = pat.sub(f"-D{key}={value}", rules)
        elif key != "BUILD_TESTING" or value != "ON":
            missing.append(f"-D{key}={value}")

    # BUILD_TESTING defaults ON upstream, but we make the contract explicit too.
    if not re.search(r"-DBUILD_TESTING=ON\b", rules):
        missing.insert(0, "-DBUILD_TESTING=ON")

    if not missing:
        return rules

    lines = rules.splitlines()
    target_idx = next((i for i, x in enumerate(lines) if re.match(r"^override_dh_auto_configure\s*:\s*$", x)), None)
    if target_idx is None:
        lines += ["", "override_dh_auto_configure:", "\tdh_auto_configure -- " + " ".join(missing)]
        return "\n".join(lines).rstrip() + "\n"

    # Add flags to the first dh_auto_configure command in the existing override.
    end = len(lines)
    for i in range(target_idx + 1, len(lines)):
        if i > target_idx + 1 and re.match(r"^[A-Za-z0-9_.%+/-][^:=]*:\s*(?:$|[^=])", lines[i]) and not lines[i].startswith(("\t", " ")):
            end = i
            break
    cmd_idx = next((i for i in range(target_idx + 1, end) if "dh_auto_configure" in lines[i] and lines[i].startswith(("\t", " "))), None)
    if cmd_idx is None:
        lines.insert(target_idx + 1, "\tdh_auto_configure -- " + " ".join(missing))
        return "\n".join(lines).rstrip() + "\n"

    # Put the flags on their own continuation line if the command is multiline;
    # otherwise append directly. Both are valid make shell recipes.
    if lines[cmd_idx].rstrip().endswith("\\"):
        j = cmd_idx
        while j + 1 < end and lines[j].rstrip().endswith("\\"):
            j += 1
        lines[j] = lines[j] + " " + " ".join(missing)
    else:
        lines[cmd_idx] = lines[cmd_idx] + (" --" if " --" not in lines[cmd_idx] else "") + " " + " ".join(missing)
    return "\n".join(lines).rstrip() + "\n"


def adapt_control(control: Path, node: str, contract: dict) -> None:
    text = control.read_text()
    parts = paragraphs(text)
    if not parts:
        raise RuntimeError("empty debian/control")

    src = parts[0]
    src = set_field(src, "Maintainer", "SupraLINUX Build System <build@supralinux.invalid>")
    for f in ("Uploaders", "Vcs-Git", "Vcs-Browser"):
        src = remove_field(src, f)
    bd = field_value(src, "Build-Depends") or ""
    if "debhelper-compat (= 14)" not in bd:
        raise RuntimeError("expected Debian 6.30 baseline debhelper-compat (= 14)")
    src = set_field(src, "Build-Depends", bd.replace("debhelper-compat (= 14)", "debhelper-compat (= 13)"))

    if node in {"kjobwidgets", "kxmlgui"}:
        build_deps = [
            "dh-sequence-python3",
            "libpyside6-dev",
            "libshiboken6-dev",
            "python3-dev",
            "pyside6-tools",
            "python3-pyside6.qtwidgets",
            "llvm-dev",
            "libclang-common-21-dev",
        ]
        if node == "kjobwidgets":
            # Required typesystem provider declared by the KDE upstream binding contract.
            build_deps.append("python3-kcoreaddons")
        for dep in build_deps:
            src = ensure_relation(src, "Build-Depends", dep)

    for override in contract.get("source_build_relation_overrides", []):
        field = override.get("field")
        if field != "Build-Depends":
            raise RuntimeError(f"{node}: unsupported source relation field: {field}")
        action = override.get("action")
        if action == "remove":
            src = remove_relation(src, field, override["package"])
        elif action == "ensure":
            src = ensure_relation(src, field, override["relation"])
        else:
            raise RuntimeError(f"{node}: unsupported source relation action: {action}")

    parts[0] = src

    for override in contract.get("binary_relation_overrides", []):
        pkg = override["package"]
        idx, para = package_para(parts, pkg)
        action = override.get("action")
        field = override.get("field")
        if action == "ensure" and field:
            relation = override.get("relation", override.get("value"))
            if not relation:
                raise RuntimeError(f"{node}: binary ensure override missing relation/value for {pkg}")
            para = ensure_relation(para, field, relation)
        elif action == "remove" and field:
            relation = override.get("relation", override.get("value"))
            if not relation:
                raise RuntimeError(f"{node}: binary remove override missing relation/value for {pkg}")
            para = remove_relation(para, field, relation_name(relation))
        elif node == "purpose" and pkg == "qml6-module-org-kde-purpose" and action == "preserve-ubuntu-optional-integration":
            para = ensure_relation(para, "Suggests", "kdeconnect")
        elif node == "purpose" and pkg == "libkf6purpose-bin" and action == "do-not-add":
            para = remove_relation(para, "Recommends", "qml6-module-org-kde-kdeconnect")
        else:
            raise RuntimeError(f"{node}: unsupported binary relation override for {pkg}: {action}/{field}")
        parts[idx] = para

    additions = contract.get("supralinux_additional_binary_packages", [])
    if node in {"kjobwidgets", "kxmlgui"}:
        expected_add = "python3-kf6jobwidgets" if node == "kjobwidgets" else "python3-kf6xmlgui"
        if additions != [expected_add]:
            raise RuntimeError(f"unexpected Python binary contract for {node}: {additions}")
        if not any(field_value(p, "Package") == expected_add for p in parts):
            runtime = ["${shlibs:Depends}", "${misc:Depends}", "${python3:Depends}", "python3-pyside6.qtwidgets"]
            if node == "kjobwidgets":
                runtime.append("python3-kcoreaddons")
            module = contract["python_module"]
            desc = "Python bindings for KDE Frameworks " + ("KJobWidgets" if node == "kjobwidgets" else "KXMLGui")
            parts.append(
                f"Package: {expected_add}\n"
                f"Section: python\n"
                f"Architecture: any\n"
                f"Depends: {', '.join(runtime)}\n"
                f"Description: {desc}\n"
                f" This package provides the upstream {module} Python extension for KDE Frameworks 6."
            )

    control.write_text("\n\n".join(p.rstrip() for p in parts) + "\n")


def apply_reference_test_suppression_overrides(rules: str, node: str, contract: dict) -> str:
    cfg = contract.get("reference_test_suppression_overrides")
    if not cfg:
        return rules

    excluded = list(cfg.get("rules_remove_excluded_tests", []))
    if excluded:
        rules = re.sub(r"(?m)^\s*(?:export\s+)?EXCLUDED_TESTS\s*=.*\n?", "", rules)
        cleaned = []
        for line in rules.splitlines():
            if "EXCLUDED_TESTS" in line and "dh_auto_test" in line:
                line = re.sub(r"\s+--\s+ARGS\+=.*$", "", line)
            cleaned.append(line)
        rules = "\n".join(cleaned).rstrip() + "\n"
        for test_name in excluded:
            if test_name in rules:
                raise RuntimeError(f"{node}: reference test exclusion remains in rules: {test_name}")
        if "EXCLUDED_TESTS" in rules:
            raise RuntimeError(f"{node}: EXCLUDED_TESTS suppression remains")
    return rules


def apply_reference_patch_suppressions(src: Path, debian: Path, node: str, contract: dict) -> None:
    cfg = contract.get("reference_patch_suppression_overrides")
    if not cfg:
        return
    names = list(cfg.get("reverse_and_drop", []))
    if not names:
        return
    series = debian / "patches" / "series"
    if not series.is_file():
        raise RuntimeError(f"{node}: patch suppression requested but debian/patches/series is missing")
    lines = series.read_text().splitlines()
    for name in names:
        patch = debian / "patches" / name
        if not patch.is_file():
            raise RuntimeError(f"{node}: reference suppression patch missing: {name}")
        if not any(x.strip() == name for x in lines):
            raise RuntimeError(f"{node}: reference suppression patch not active in series: {name}")
        run(["patch", "-p1", "-R", "--batch", "--no-backup-if-mismatch", "-i", patch], cwd=src)
        lines = [x for x in lines if x.strip() != name]
        patch.unlink()
    series.write_text("\n".join(lines).rstrip() + ("\n" if lines else ""))
    active = [x.strip() for x in lines if x.strip() and not x.lstrip().startswith("#")]
    if active:
        raise RuntimeError(f"{node}: selective patch suppression currently requires no remaining active patches: {active}")
    shutil.rmtree(src / ".pc", ignore_errors=True)


def apply_symbol_template_overrides(debian: Path, node: str, contract: dict) -> None:
    for override in contract.get("symbol_template_overrides", []):
        package = override["package"]
        symbol = override["symbol"]
        path = debian / f"{package}.symbols"
        if not path.is_file():
            raise RuntimeError(f"{node}: symbols template missing for {package}")
        lines = path.read_text().splitlines()
        matches = [i for i, line in enumerate(lines) if symbol in line]
        if len(matches) != 1:
            raise RuntimeError(f"{node}: expected one symbols entry for {symbol}, got {len(matches)}")
        i = matches[0]
        line = lines[i]
        leading = line[:len(line) - len(line.lstrip())]
        body = line.strip()
        pos = body.find(symbol)
        prefix = body[:pos]
        suffix = body[pos:]
        tags = []
        if prefix:
            if not (prefix.startswith("(") and prefix.endswith(")")):
                raise RuntimeError(f"{node}: unsupported symbols prefix for {symbol}: {prefix}")
            tags = [x for x in prefix[1:-1].split("|") if x]
        for required in override.get("preserve_tags", []):
            if required not in tags:
                raise RuntimeError(f"{node}: expected symbols tag missing for {symbol}: {required}")
        for tag in override.get("add_tags", []):
            if tag not in tags:
                tags.insert(0, tag)
        lines[i] = leading + "(" + "|".join(tags) + ")" + suffix
        path.write_text("\n".join(lines) + "\n")


def validate_remediation_overrides(control: Path, debian: Path, rules: str, node: str, contract: dict) -> None:
    parts = paragraphs(control.read_text())
    src = parts[0]
    build_depends = field_value(src, "Build-Depends") or ""
    relation_names = {relation_name(x) for x in split_relations(build_depends)}
    for override in contract.get("source_build_relation_overrides", []):
        action = override.get("action")
        if action == "remove":
            if override["package"] in relation_names:
                raise RuntimeError(f"{node}: removed Build-Depends still present: {override['package']}")
        elif action == "ensure":
            wanted = relation_name(override["relation"])
            if wanted not in relation_names:
                raise RuntimeError(f"{node}: required Build-Depends missing: {wanted}")

    test_cfg = contract.get("reference_test_suppression_overrides", {})
    for test_name in test_cfg.get("rules_remove_excluded_tests", []):
        if test_name in rules or "EXCLUDED_TESTS" in rules:
            raise RuntimeError(f"{node}: reference test suppression remains: {test_name}")

    patch_cfg = contract.get("reference_patch_suppression_overrides", {})
    series = debian / "patches" / "series"
    series_text = series.read_text() if series.is_file() else ""
    for name in patch_cfg.get("reverse_and_drop", []):
        if name in series_text or (debian / "patches" / name).exists():
            raise RuntimeError(f"{node}: reference QSKIP patch remains: {name}")

    for override in contract.get("symbol_template_overrides", []):
        package = override["package"]
        symbol = override["symbol"]
        path = debian / f"{package}.symbols"
        matches = [line for line in path.read_text().splitlines() if symbol in line]
        if len(matches) != 1:
            raise RuntimeError(f"{node}: symbols override validation mismatch for {symbol}")
        line = matches[0]
        for tag in override.get("add_tags", []) + override.get("preserve_tags", []):
            if tag not in line:
                raise RuntimeError(f"{node}: symbols override tag missing for {symbol}: {tag}")


def validate_control(control: Path, node: str, contract: dict) -> None:
    parts = paragraphs(control.read_text())
    names = [field_value(p, "Package") for p in parts[1:] if field_value(p, "Package")]
    if names != contract["target_binary_packages"]:
        raise RuntimeError(f"binary package set/order mismatch expected={contract['target_binary_packages']} actual={names}")
    src = parts[0]
    if "debhelper-compat (= 14)" in (field_value(src, "Build-Depends") or ""):
        raise RuntimeError("debhelper compat 14 remains")
    if "debhelper-compat (= 13)" not in (field_value(src, "Build-Depends") or ""):
        raise RuntimeError("debhelper compat 13 missing")
    if field_value(src, "Maintainer") != "SupraLINUX Build System <build@supralinux.invalid>":
        raise RuntimeError("SupraLINUX maintainer missing")
    for f in ("Uploaders", "Vcs-Git", "Vcs-Browser"):
        if field_value(src, f) is not None:
            raise RuntimeError(f"reference metadata remains: {f}")

    for override in contract.get("binary_relation_overrides", []):
        pkg = override["package"]
        idx, para = package_para(parts, pkg)
        field = override.get("field")
        action = override.get("action")
        if action in {"ensure", "remove"} and field:
            relation = override.get("relation", override.get("value"))
            wanted = relation_name(relation)
            present = any(relation_name(x) == wanted for x in split_relations(field_value(para, field)))
            if action == "ensure" and not present:
                raise RuntimeError(f"{node}: binary relation ensure failed for {pkg}: {field} {wanted}")
            if action == "remove" and present:
                raise RuntimeError(f"{node}: binary relation removal failed for {pkg}: {field} {wanted}")

    if node == "kio":
        _, p = package_para(parts, "kio6")
        if not any(relation_name(x) == "kwallet6" for x in split_relations(field_value(p, "Depends"))):
            raise RuntimeError("KIO selected-profile kwallet6 runtime dependency missing")
    if node == "purpose":
        _, qml = package_para(parts, "qml6-module-org-kde-purpose")
        if not any(relation_name(x) == "kdeconnect" for x in split_relations(field_value(qml, "Suggests"))):
            raise RuntimeError("Purpose optional KDE Connect Suggests missing")
        _, binp = package_para(parts, "libkf6purpose-bin")
        if any(relation_name(x) == "qml6-module-org-kde-kdeconnect" for x in split_relations(field_value(binp, "Recommends"))):
            raise RuntimeError("Purpose must not recommend KDE Connect QML provider")
    if node in {"kjobwidgets", "kxmlgui"}:
        src_bd = field_value(src, "Build-Depends") or ""
        for dep in ("dh-sequence-python3", "libpyside6-dev", "libshiboken6-dev", "python3-dev", "pyside6-tools", "python3-pyside6.qtwidgets", "llvm-dev", "libclang-common-21-dev"):
            if dep not in src_bd:
                raise RuntimeError(f"{node}: Python binding build provider missing: {dep}")
        if node == "kjobwidgets" and "python3-kcoreaddons" not in src_bd:
            raise RuntimeError("kjobwidgets: KCoreAddons Python typesystem provider missing")
        if node == "kjobwidgets" and "python3-build" not in src_bd:
            raise RuntimeError("kjobwidgets: Python build frontend provider missing")
        if node == "kjobwidgets" and contract.get("package_version_candidate") == "6.30.0-0supralinux3" and "python3-setuptools" not in src_bd:
            raise RuntimeError("kjobwidgets: setuptools build backend provider missing")


def write_changelog(path: Path, source: str, version: str, node: str) -> None:
    entry = f"""{source} ({version}) resolute; urgency=medium

  * SupraLINUX KDE Frameworks 6.30 Tier 3 source materialization for {node}.
  * Preserve KDE upstream source/features and apply only documented SupraLINUX
    contract/provider adaptations for Ubuntu 26.04 Resolute.

 -- SupraLINUX Build System <build@supralinux.invalid>  Tue, 22 Sep 2026 12:00:00 +0000

"""
    path.write_text(entry + path.read_text())


def deterministic_source_tree(src: Path, out: Path) -> None:
    # Python tarfile gives deterministic metadata without relying on GNU tar extensions.
    with tarfile.open(out, "w:xz", format=tarfile.PAX_FORMAT) as tf:
        for p in sorted([src, *src.rglob("*")], key=lambda x: x.relative_to(src.parent).as_posix()):
            arc = p.relative_to(src.parent).as_posix()
            info = tf.gettarinfo(str(p), arcname=arc)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if p.is_file() and not p.is_symlink():
                with p.open("rb") as f:
                    tf.addfile(info, f)
            else:
                tf.addfile(info)


def write_result(result: str, stage: str, exit_code: int, **extra) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "result.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}
    data.update({
        "result": result,
        "exit_code": exit_code,
        "stage": stage,
        "node": NODE,
        "claim": "tier3-source-materialization-only",
        "package_attempted": False,
        "package_state_effect": "none",
    })
    data.update(extra)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> None:
    global STAGE
    if not NODE:
        raise SystemExit(f"Usage: {sys.argv[0]} <node>")
    if not MANIFEST.exists() or not CONTRACTS.exists() or not CANONICAL.exists():
        raise RuntimeError("required Tier 3 manifests missing")

    manifest = json.loads(MANIFEST.read_text())
    contracts = json.loads(CONTRACTS.read_text())
    canonical = json.loads(CANONICAL.read_text())
    if NODE not in manifest["selected_nodes"]:
        raise RuntimeError(f"unknown Tier 3 node: {NODE}")
    contract = contracts["nodes"][NODE]
    cnode = next(x for x in canonical["nodes"] if x["id"] == NODE)
    if contract.get("contract_state") != "contract-ready":
        raise RuntimeError("contract is not materialization-ready")
    if contracts.get("contract_decision", {}).get("materialization_authorized") is not True:
        raise RuntimeError("materialization is not authorized")
    if contracts.get("contract_decision", {}).get("package_build_authorized") is not False:
        raise RuntimeError("materialization lane must not run after binary builds are authorized")

    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(EVIDENCE, ignore_errors=True)
    (WORK / "reference").mkdir(parents=True)
    (WORK / "source").mkdir(parents=True)
    EVIDENCE.mkdir(parents=True)

    # Mirror stdout/stderr into the retained artifact without hiding live logs.
    log = (EVIDENCE / "pipeline.log").open("w")
    class Tee:
        def __init__(self, *files): self.files = files
        def write(self, s):
            for f in self.files: f.write(s); f.flush()
            return len(s)
        def flush(self):
            for f in self.files: f.flush()
    sys.stdout = Tee(sys.__stdout__, log)
    sys.stderr = Tee(sys.__stderr__, log)

    try:
        STAGE = "platform-check"
        osr = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1); osr[k] = v.strip().strip('"')
        if osr.get("ID") != "ubuntu" or osr.get("VERSION_ID") != "26.04":
            raise RuntimeError("expected Ubuntu 26.04 materialization runner")
        run([sys.executable, ROOT / "scripts/validate_kde_tier3_materialization.py"])

        source_package = contract["source_package"]
        ref = contract["technical_references"]["debian"]
        reference_version = ref["version"]
        package_version = contract["package_version_candidate"]
        upstream_version = contract["upstream_version"]
        upstream_sha = contract["source_sha256"]
        upstream_url = cnode["source_url"]
        baseline_tree_sha = contract["packaging_baseline"]["tree_sha256"]

        STAGE = "apt-reference-setup"
        source_list = WORK / "debian.sources.list"
        lists = WORK / "apt-lists-debian"
        source_list.write_text("deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main\n")
        lists.mkdir()
        run(["sudo", "chown", "_apt:root", lists])
        apt_opts = [
            "-o", f"Dir::Etc::sourcelist={source_list}",
            "-o", "Dir::Etc::sourceparts=-",
            "-o", f"Dir::State::lists={lists}",
            "-o", "APT::Get::List-Cleanup=0",
        ]
        run(["sudo", "apt-get", *apt_opts, "update"])

        STAGE = "kde-source-download"
        official = WORK / "source" / f"{NODE}-{upstream_version}.tar.xz"
        run(["curl", "-fL", "--retry", "3", "--retry-delay", "2", "-o", official, upstream_url])
        actual = sha256(official)
        if actual != upstream_sha:
            raise RuntimeError(f"KDE upstream source SHA mismatch: {actual} != {upstream_sha}")

        STAGE = "debian-baseline-download"
        refdir = WORK / "reference"
        run(["apt-get", *apt_opts, "source", "--download-only", f"{source_package}={reference_version}"], cwd=refdir)
        pinned = {
            ref["dsc_file"]: ref["dsc_sha256"],
            ref["debian_tar_file"]: ref["debian_tar_sha256"],
            ref["orig_tar_file"]: ref["orig_tar_sha256"],
        }
        for name, expected in pinned.items():
            p = refdir / name
            if not p.is_file():
                raise RuntimeError(f"pinned Debian source file missing: {name}")
            got = sha256(p)
            if got != expected:
                raise RuntimeError(f"pinned Debian source SHA mismatch for {name}: {got} != {expected}")
        if ref["orig_tar_sha256"] != upstream_sha:
            raise RuntimeError("Debian orig tar does not match KDE upstream authority")

        STAGE = "baseline-extract"
        src = WORK / "source" / f"{source_package}-{upstream_version}"
        run(["dpkg-source", "-x", refdir / ref["dsc_file"], src])
        debian = src / "debian"
        before_tree_sha, before_rows = tree_record(debian)
        if before_tree_sha != baseline_tree_sha:
            raise RuntimeError(f"Debian packaging tree SHA mismatch: {before_tree_sha} != {baseline_tree_sha}")
        (EVIDENCE / "baseline-tree.json").write_text(json.dumps(before_rows, indent=2, sort_keys=True) + "\n")

        # Use the independently downloaded KDE tarball as the orig artifact used for output.
        orig_name = ref["orig_tar_file"]
        orig_out = WORK / "source" / orig_name
        shutil.copy2(official, orig_out)

        STAGE = "contract-adaptation"
        control = debian / "control"
        rules = debian / "rules"
        changelog = debian / "changelog"
        adapt_control(control, NODE, contract)
        apply_reference_patch_suppressions(src, debian, NODE, contract)
        rules_text = sanitize_test_suppression(rules.read_text())
        rules_text = apply_reference_test_suppression_overrides(rules_text, NODE, contract)
        rules_text = cmake_flags(rules_text, contract.get("selected_profile", {}))
        validate_test_policy(rules_text)
        rules.write_text(rules_text)
        apply_symbol_template_overrides(debian, NODE, contract)
        write_changelog(changelog, source_package, package_version, NODE)

        if NODE in {"kjobwidgets", "kxmlgui"}:
            pkg = contract["supralinux_additional_binary_packages"][0]
            module = contract["python_module"]
            (debian / f"{pkg}.install").write_text(f"usr/lib/python3/dist-packages/{module}*.so\n")

        validate_control(control, NODE, contract)
        validate_remediation_overrides(control, debian, rules.read_text(), NODE, contract)
        if "-DBUILD_TESTING=OFF" in rules.read_text():
            raise RuntimeError("reference BUILD_TESTING=OFF suppression remains")
        for key, value in contract.get("selected_profile", {}).items():
            if isinstance(value, bool) and value and key != "BUILD_TESTING":
                if f"-D{key}=ON" not in rules.read_text():
                    raise RuntimeError(f"selected profile flag not explicitly materialized: {key}=ON")
        if "-DBUILD_TESTING=ON" not in rules.read_text():
            raise RuntimeError("BUILD_TESTING=ON not explicitly materialized")

        # Ensure changelog version is exactly the candidate contract.
        parsed = run(["dpkg-parsechangelog", "-l" + str(changelog), "-S", "Version"], capture=True).stdout.strip()
        if parsed != package_version:
            raise RuntimeError(f"changelog version mismatch: {parsed} != {package_version}")

        STAGE = "source-package-build"
        run(["dpkg-source", "-b", src], cwd=WORK / "source")
        normalized = package_version.split(":", 1)[-1]
        dsc = WORK / "source" / f"{source_package}_{normalized}.dsc"
        candidates = sorted((WORK / "source").glob(f"{source_package}_{normalized}.debian.tar.*"))
        if not dsc.is_file() or len(candidates) != 1:
            raise RuntimeError("materialized source package artifacts missing or ambiguous")
        debtar = candidates[0]

        STAGE = "evidence"
        after_tree_sha, after_rows = tree_record(debian)
        (EVIDENCE / "materialized-tree.json").write_text(json.dumps(after_rows, indent=2, sort_keys=True) + "\n")
        source_tree = EVIDENCE / f"{source_package}_{normalized}.source-tree.tar.xz"
        deterministic_source_tree(src, source_tree)
        for p in (dsc, debtar, orig_out):
            shutil.copy2(p, EVIDENCE / p.name)
        shutil.copytree(debian, EVIDENCE / "debian", symlinks=True)

        evidence = {
            "source_package": source_package,
            "package_version": package_version,
            "upstream_version": upstream_version,
            "upstream_source_url": upstream_url,
            "orig_tar_sha256": sha256(orig_out),
            "reference_tree_sha256": before_tree_sha,
            "materialized_tree_sha256": after_tree_sha,
            "dsc_sha256": sha256(EVIDENCE / dsc.name),
            "debian_tar_sha256": sha256(EVIDENCE / debtar.name),
            "source_tree_sha256": sha256(source_tree),
            "adapted_control_sha256": sha256(control),
            "adapted_rules_sha256": sha256(rules),
            "selected_profile": contract.get("selected_profile", {}),
            "target_binary_packages": contract["target_binary_packages"],
            "source_build_relation_overrides": contract.get("source_build_relation_overrides", []),
            "reference_test_suppression_overrides": contract.get("reference_test_suppression_overrides"),
            "reference_patch_suppression_overrides": contract.get("reference_patch_suppression_overrides"),
            "symbol_template_overrides": contract.get("symbol_template_overrides", []),
            "stable_promotion_requires_explicit_user_approval": True,
        }
        if evidence["orig_tar_sha256"] != upstream_sha:
            raise RuntimeError("authoritative KDE source changed during materialization")
        write_result("PASS", "complete", 0, **evidence)
        files = [p for p in EVIDENCE.iterdir() if p.is_file() and p.name != "artifact-sha256.txt"]
        (EVIDENCE / "artifact-sha256.txt").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(files)))
        print(json.dumps(json.loads((EVIDENCE / "result.json").read_text()), indent=2))
        print(f"Tier 3 materialization {NODE}: PASS")
    except Exception as exc:
        write_result("FAIL", STAGE, 1, error=str(exc))
        raise
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        log.close()


if __name__ == "__main__":
    main()
