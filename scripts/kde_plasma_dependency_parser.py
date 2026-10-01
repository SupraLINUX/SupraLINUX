#!/usr/bin/env python3
"""Pure CMake find_package/find_dependency parser for Plasma planning."""

import re

FIND_CALL_RE = re.compile(
    r"\b(?:find_package|find_dependency)\s*\(\s*([^\)]+)\)",
    re.IGNORECASE | re.DOTALL,
)

FIND_COMPONENT_STOP = {
    "CONFIG",
    "NO_MODULE",
    "MODULE",
    "NO_POLICY_SCOPE",
    "BYPASS_PROVIDER",
    "NAMES",
    "HINTS",
    "PATHS",
    "PATH_SUFFIXES",
    "REGISTRY_VIEW",
    "GLOBAL",
}


def parse_find_packages(cmake: str):
    packages = set()
    required_components = {}
    optional_components = {}

    for body in FIND_CALL_RE.findall(cmake):
        tokens = re.findall(r'"[^"]*"|\S+', body.replace("\n", " "))
        tokens = [
            token.strip().strip('"').rstrip(",")
            for token in tokens
            if token.strip()
        ]
        if not tokens:
            continue

        package = tokens[0]
        packages.add(package)
        mode = None

        for token in tokens[1:]:
            upper = token.upper()

            if upper == "COMPONENTS":
                mode = "required"
                continue
            if upper == "OPTIONAL_COMPONENTS":
                mode = "optional"
                continue

            # REQUIRED/QUIET/EXACT are modifiers and do not terminate a
            # component list if upstream places them after COMPONENTS.
            if upper in {"REQUIRED", "QUIET", "EXACT"}:
                continue

            if upper in FIND_COMPONENT_STOP:
                mode = None
                continue

            if mode is None:
                continue
            if token.startswith("$") or token.startswith("${"):
                continue
            if not re.fullmatch(r"[A-Za-z0-9_.+:-]+", token):
                continue

            target = (
                required_components
                if mode == "required"
                else optional_components
            )
            target.setdefault(package, set()).add(token)

    return (
        sorted(packages),
        {
            key: sorted(value)
            for key, value in sorted(required_components.items())
        },
        {
            key: sorted(value)
            for key, value in sorted(optional_components.items())
        },
    )
