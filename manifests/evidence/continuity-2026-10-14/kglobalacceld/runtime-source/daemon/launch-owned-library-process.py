#!/usr/bin/env python3
"""Restore only reviewed runtime paths inside an owned private X11 fixture."""
import argparse
import json
import os
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--config', type=Path, required=True)
p.add_argument('--phase', required=True)
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
root = Path(__file__).resolve().parent
assert a.config.resolve().is_relative_to(root)
config = json.loads(a.config.read_text())
command = a.command[1:] if a.command[:1] == ['--'] else a.command
assert command and Path(command[0]).resolve().is_relative_to(root)
home = Path(os.environ['HOME'])
assert home.parent.name.startswith('supra-shortcuts-private-')
paths = config['phases'][a.phase]
environment = os.environ.copy()
for key, values in paths.items():
    assert key in {'LD_LIBRARY_PATH', 'QT_PLUGIN_PATH', 'LIBGL_DRIVERS_PATH', '__EGL_VENDOR_LIBRARY_FILENAMES'}
    for value in values:
        assert Path(value).resolve().is_relative_to(root) and Path(value).exists()
    environment[key] = ':'.join(values)
environment.update(LD_DEBUG='libs', LD_BIND_NOW='1', LIBGL_ALWAYS_SOFTWARE='1')
os.execve(command[0], command, environment)
