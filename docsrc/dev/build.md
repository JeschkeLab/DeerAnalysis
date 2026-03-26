


```
python -m PyInstaller --noconfirm DeerAnalysis_MacOS.spec
```


Create a DMG file for macOS distribution:
```
hdiutil create -volname "DeerAnalysis2026" -srcfolder "dist/DeerAnalysis.app" -ov -format UDZO "dist/DeerAnalysis2026_MacOS.dmg"            
```