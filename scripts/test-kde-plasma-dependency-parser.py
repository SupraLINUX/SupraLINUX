#!/usr/bin/env python3
from kde_plasma_dependency_parser import parse_find_packages

sample = r"""
find_package(KF6 6.26 REQUIRED
    COMPONENTS Config CoreAddons KIO
)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core Gui
    OPTIONAL_COMPONENTS WaylandClient
)
find_dependency(KF6WindowSystem 6.26 REQUIRED)
find_package(Foo QUIET COMPONENTS Bar Baz)
find_package(VariablePackage REQUIRED COMPONENTS ${DYNAMIC_COMPONENT})
"""

packages, required, optional = parse_find_packages(sample)

expected_packages = [
    "Foo",
    "KF6",
    "KF6WindowSystem",
    "Qt6",
    "VariablePackage",
]
assert packages == expected_packages, (packages, expected_packages)
assert required["KF6"] == ["Config", "CoreAddons", "KIO"], required
assert required["Qt6"] == ["Core", "Gui"], required
assert optional["Qt6"] == ["WaylandClient"], optional
assert required["Foo"] == ["Bar", "Baz"], required
assert "VariablePackage" not in required, required
assert "KF6WindowSystem" not in required, required

print("KDE Plasma dependency parser self-test: PASS")
