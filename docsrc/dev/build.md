


```
pyinstaller --noconfirm DeerAnalysis.spec
```


Create a DMG file for macOS distribution:
```
hdiutil create -volname "DeerAnalysis2026" -srcfolder "dist/DeerAnalysis.app" -ov -format UDZO "DeerAnalysis2026.dmg"             
```