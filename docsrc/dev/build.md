


1. Build virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate # .\.venv\Scripts\Activate.ps1
pip install ../DeerLab
pip install ../PyEPR
pip install .
pip install pyinstaller
```

2. a) MacOS
```
python -m PyInstaller --noconfirm DeerAnalysis_MacOS.spec
```

Create a DMG file for macOS distribution:
```
hdiutil create -volname "DeerAnalysis2026" -srcfolder "dist/DeerAnalysis.app" -ov -format UDZO "dist/DeerAnalysis2026_MacOS.dmg"            
```
2. b) Windows
```
python -m PyInstaller --noconfirm DeerAnalysis_Win.spec
```

