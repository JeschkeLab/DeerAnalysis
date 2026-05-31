


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

2. c) Linux

First you need to install the required dependencies for Linux. For example, on Ubuntu you can run:
```
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
sudo apt install libcanberra-gtk-module libcanberra-gtk3-module
sudo apt install libgirepository-2.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0 libgirepository1.0-dev
sudo apt install libwebkit2gtk-4.1-dev gir1.2-webkit2-4.1
```

```
pip install pywebview[gtk]
```

```
python -m PyInstaller --noconfirm DeerAnalysis_Linux.spec
```

2. d) Linux — Flatpak

See [flatpak_package.md](flatpak_package.md).

