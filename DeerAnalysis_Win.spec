from PyInstaller.utils.hooks import collect_data_files,collect_submodules

datas = [('src/deeranalysis/assets', 'deeranalysis/assets')]
datas += [('src/deeranalysis/pages', 'deeranalysis/pages')]  # Add pages folder
datas += [('src/deeranalysis/components', 'deeranalysis/components')]  # Add pages folder

datas += collect_data_files('dash_iconify')
datas += collect_data_files('dash_mantine_components')
datas += collect_data_files('dash_ag_grid')
datas += collect_data_files('deerlab')  # Collect deerlab data files



# Collect all submodules from deeranalysis package
hiddenimports = ['dash_iconify', 'deerlab','pyepr-esr', 'dash_ag_grid']
hiddenimports += collect_submodules('deeranalysis')
hiddenimports += collect_submodules('deerlab')  # Properly collect all deerlab submodules

excludes = [
    'webview.platforms.gtk',
    'webview.platforms.qt',
    'webview.platforms.cef',
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
    ['src/deeranalysis/main.py'],
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

splash = Splash(
    'src/deeranalysis/assets/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DeerAnalysis 2026',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    exclude_binaries=False,  # Must be False for one-file
    icon='src/deeranalysis/assets/favicon.ico',  # Add this line
)

