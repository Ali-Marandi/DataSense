# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for the DataSense Windows executable."""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("sklearn.utils")
    + collect_submodules("scipy.special")
    + ["sklearn.ensemble", "sklearn.tree", "sklearn.svm", "sklearn.linear_model", "pyarrow"]
)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[("assets/icon.ico", "assets"), ("assets/icon.png", "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PySide6", "notebook", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DataSense",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="DataSense",
)
