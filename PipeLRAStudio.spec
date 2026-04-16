# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Collect VTK and PySide6 assets
datas_vtk, binaries_vtk, hiddenimports_vtk = collect_all('vtk')
datas_pyside, binaries_pyside, hiddenimports_pyside = collect_all('PySide6')

block_cipher = None

a = Analysis(
    ['pipe_lra_studio/src/main.py'],
    pathex=[],
    binaries=binaries_vtk + binaries_pyside,
    datas=datas_vtk + datas_pyside,
    hiddenimports=hiddenimports_vtk + hiddenimports_pyside + ['fpdf2', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PipeLRAStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to False for Windowed mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=['icon.ico'], # Add an icon if you have one
)
