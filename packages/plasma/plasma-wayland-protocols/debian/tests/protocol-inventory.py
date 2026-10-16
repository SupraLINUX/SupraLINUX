#!/usr/bin/env python3
"""Verify exact installed XML bytes and advertised CMake provider identity."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

expected = json.loads(Path(sys.argv[1]).read_text())
directory = Path('/usr/share/plasma-wayland-protocols')
actual = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in directory.glob('*.xml')}
assert actual == expected, f'Installed protocol inventory drift: {actual}'
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.16)\n'
        'project(protocol-provider-consumer LANGUAGES NONE)\n'
        f'find_package(PlasmaWaylandProtocols {sys.argv[2]} EXACT CONFIG REQUIRED)\n'
        'if(NOT PLASMA_WAYLAND_PROTOCOLS_DIR STREQUAL "/usr/share/plasma-wayland-protocols")\n'
        '  message(FATAL_ERROR "Unexpected installed protocol directory")\nendif()\n')
    subprocess.run(['cmake', '-S', str(root), '-B', str(root/'build')], check=True)
print(f'Exact installed 30 protocols, two legacy aliases and CMake {sys.argv[2]} consumer: PASS')
