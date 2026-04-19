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

# 排除用不到但 PyInstaller hooks 会强行拉入的重量级依赖
# 实测可节省 5-8GB 打包体积, 让 GitHub Actions Runner 能跑完 onefile 构建
excludes = [
    # 深度学习框架的无关部分
    'tensorflow', 'tensorflow_core', 'tensorboard', 'tensorboardX',
    'onnxruntime', 'onnx', 'triton',
    # NVIDIA CUDA 运行时 (用户若无 GPU 也能跑 CPU 推理)
    'nvidia.cudnn', 'nvidia.cusparselt', 'nvidia.nccl', 'nvidia.nvshmem',
    'nvidia.cublas', 'nvidia.cufft', 'nvidia.curand', 'nvidia.cusolver',
    'nvidia.cusparse', 'nvidia.nvjitlink', 'nvidia.nvtx',
    # Jupyter / IPython 交互环境
    'IPython', 'ipykernel', 'ipywidgets', 'jupyter', 'jupyter_client',
    'jupyter_core', 'notebook', 'nbformat', 'nbconvert', 'qtconsole',
    'jedi', 'parso', 'prompt_toolkit',
    # 测试框架
    'pytest', 'pytest_asyncio', '_pytest', 'py',
    # GUI (纯命令行服务不需要)
    'tkinter', '_tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    'matplotlib.backends._backend_tk', 'matplotlib.backends.backend_qt5agg',
    # 其他少用
    'pandas.tests', 'numpy.tests', 'scipy.tests', 'sklearn.tests',
]

a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
