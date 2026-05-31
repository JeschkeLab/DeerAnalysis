import tomllib
import os

ROOT = os.path.normpath(os.path.join(SPECPATH, '..', '..'))

with open(os.path.join(ROOT, 'pyproject.toml'), 'rb') as f:
    _pyproject = tomllib.load(f)
version = _pyproject['project']['version']

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = [(os.path.join(ROOT, 'src/deeranalysis/assets'), 'deeranalysis/assets')]
datas += [(os.path.join(ROOT, 'src/deeranalysis/pages'), 'deeranalysis/pages')]
datas += [(os.path.join(ROOT, 'src/deeranalysis/components'), 'deeranalysis/components')]

datas += collect_data_files('dash_iconify')
datas += collect_data_files('dash_mantine_components')
datas += collect_data_files('dash_ag_grid')
datas += collect_data_files('deerlab')  # Collect deerlab data files
datas += copy_metadata('deeranalysis')
datas += copy_metadata('deerlab')

# Collect all submodules from deeranalysis package
hiddenimports = ['dash_iconify', 'deerlab','pyepr-esr', 'dash_ag_grid']
hiddenimports += collect_submodules('deeranalysis')
hiddenimports += collect_submodules('deerlab')  # Properly collect all deerlab submodules

excludes = [
    # Exclude other pywebview backends not needed on macOS
    'webview.platforms.gtk',
    'webview.platforms.qt',
    'webview.platforms.cef',
    'webview.platforms.edgechromium',
    'webview.platforms.winforms',
    # Exclude unused GUI frameworks
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'gi',
    'cefpython3',
    'tkinter',
#    'numba',
#    'llvmlite',
]

a = Analysis(
    [os.path.join(ROOT, 'src/deeranalysis/main.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DeerAnalysis 2026',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Change to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DeerAnalysis_dist',
)
app = BUNDLE(
    coll,
    name='DeerAnalysis.app',
    icon=os.path.join(ROOT, 'src/deeranalysis/assets/favicon.ico'),
    bundle_identifier='com.deeranalysis.app',
    version=version,
    info_plist={
        'CFBundleShortVersionString': version,
        'CFBundleVersion': version,
        'NSHumanReadableCopyright': 'Copyright © 2026 ETH Zürich, UNIGE, Hugo Karas. All rights reserved.',
    },
)
