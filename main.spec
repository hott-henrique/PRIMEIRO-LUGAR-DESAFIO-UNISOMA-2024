# -*- mode: python ; coding: utf-8 -*-
import sys
import os

def get_pulp_path():
    import pulp
    return pulp.__path__[0]

path_main = os.path.dirname(os.path.abspath(sys.argv[0]))

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pandas', 'pulp', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.datas += Tree(get_pulp_path(), prefix='pulp', excludes=["*.pyc"])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
