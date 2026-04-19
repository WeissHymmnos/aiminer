# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

is_win = sys.platform.startswith('win')
is_mac = sys.platform.startswith('darwin')
ext = '.pyd' if is_win else '.so'

hidden_imports = collect_submodules('agents') + \
                 collect_submodules('core') + \
                 collect_submodules('schemas') + \
                 collect_submodules('app_workflow') + \
                 ['uvicorn.protocols.http.httptools_impl',
                  'uvicorn.protocols.http.h11_impl',
                  'uvicorn.protocols.websockets.wsproto_impl',
                  'uvicorn.lifespan.on',
                  'uvicorn.lifespan.off',
                  'uvicorn.loops.auto',
                  'uvicorn.loops.asyncio',
                  'polars_plugins']

datas = [
    ('data/rag_docs/templates', 'data/rag_docs/templates'),
    ('.env.example', '.'),
]

# Rust 插件: 先尝试从 site-packages 收集 (CI 中通过 pip install wheel 安装),
# 失败再回退到本地 maturin 构建产物
binaries = list(collect_dynamic_libs('polars_plugins'))

if not binaries:
    fallback_globs = [
        'polars_plugins/target/release/libpolars_plugins.*',
        'polars_plugins/target/release/polars_plugins.*',
        f'dist_plugins/polars_plugins*{ext}',
    ]
    for pattern in fallback_globs:
        for p in glob.glob(pattern):
            if p.endswith(('.so', '.dylib', '.pyd')):
                binaries.append((p, '.'))
                break
        if binaries:
            break

a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
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
    name='aiminer-backend',
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
