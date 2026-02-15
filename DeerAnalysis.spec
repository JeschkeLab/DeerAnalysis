from PyInstaller.utils.hooks import collect_data_files,collect_submodules

datas = [('src/deeranalysis/assets', 'deeranalysis/assets')]
datas += [('src/deeranalysis/pages', 'deeranalysis/pages')]  # Add pages folder
datas += [('src/deeranalysis/components', 'deeranalysis/components')]  # Add pages folder

datas += collect_data_files('dash_iconify')
datas += collect_data_files('dash_mantine_components')
datas += collect_data_files('dash_ag_grid')


# Collect all submodules from deeranalysis package
hiddenimports = ['dash_iconify', 'deerlab', 'autodeer','pyepr-esr', 'dash_ag_grid']
hiddenimports += collect_submodules('deeranalysis')


a = Analysis(
    ['src/deeranalysis/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DeerAnalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Change to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='DeerAnalysis.app',
    icon=None,
    bundle_identifier=None,
)
