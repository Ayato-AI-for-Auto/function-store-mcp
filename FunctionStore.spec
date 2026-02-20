# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base directory
base_dir = os.path.abspath(os.getcwd())

# Collect backend and frontend datas
# Format: (source_path, destination_folder)
datas = [
    ('backend/mcp_core', 'mcp_core'),
    ('frontend', 'frontend'),
    ('README.md', '.'),
]

# Collect additional data for flet and other libs if needed
datas += collect_data_files('flet')
datas += collect_data_files('duckdb')

hiddenimports = [
    'flet',
    'flet_runtime',
    'duckdb',
    'onnxruntime',
    'onnx',
    'numpy',
    'ruamel.yaml',
    'ruff',
    'msvcrt',
]
hiddenimports += collect_submodules('mcp_core')

a = Analysis(
    ['main.py'],
    pathex=[os.path.join(base_dir, 'backend')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='FunctionStore',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Changed to True for MCP stdio support
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
)
