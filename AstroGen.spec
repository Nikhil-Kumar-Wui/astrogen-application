# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\frontend\\main.py'],
    pathex=['C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1'],
    binaries=[],
    datas=[('C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\frontend\\artifacts\\astrogen\\dist\\public', 'backend/dist'), ('C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\frontend\\logo.ico', 'frontend'), ('C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\.env', '.'), ('C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\backend', 'backend')],
    hiddenimports=[],
    hookspath=['C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\scripts\\hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch.utils.benchmark.utils.valgrind_wrapper', 'torch.utils.benchmark'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AstroGen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\harsh\\Desktop\\NTCC - In House\\APPLICATION\\APP 5\\PROJECT1\\frontend\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AstroGen',
)
