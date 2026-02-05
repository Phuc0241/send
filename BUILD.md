# Build Instructions for Send Anywhere Python

## Quick Build

**Double-click:** `build.bat`

Or run:
```powershell
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install pyinstaller
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m PyInstaller build_config.spec --clean
```

## Output

Executable will be created in:
```
dist\SendAnywhere\SendAnywhere.exe
```

## Distribution

Copy the entire `dist\SendAnywhere\` folder to distribute. It contains:
- `SendAnywhere.exe` - Main executable
- `static\` - Web UI files
- All required DLLs and dependencies

## Running the Executable

```powershell
cd dist\SendAnywhere
SendAnywhere.exe
```

This will:
1. Start Relay Server (Port 8000)
2. Start Signaling Server (Port 3000)
3. Start Web UI (Port 5001)

Then open browser: `http://localhost:5001`

## File Size

Expected size: ~50-80 MB (includes Python runtime + all dependencies)

## Advanced Build Options

### Build Single File (Slower startup, but single .exe)

```powershell
pyinstaller --onefile --add-data "static;static" start_all_servers.py
```

### Build with Icon

```powershell
pyinstaller build_config.spec --icon=icon.ico
```

### Reduce Size (Remove debug symbols)

```powershell
pyinstaller build_config.spec --strip
```

## Troubleshooting

### Missing Modules Error

Add to `hiddenimports` in `build_config.spec`:
```python
hiddenimports=['missing_module_name']
```

### Static Files Not Found

Ensure `datas` includes static folder:
```python
datas=[('static', 'static')]
```

### Antivirus False Positive

PyInstaller executables may trigger antivirus. Add exception or sign the executable.

## Build for Distribution

For production distribution:

1. **Build**
   ```powershell
   build.bat
   ```

2. **Test**
   ```powershell
   cd dist\SendAnywhere
   SendAnywhere.exe
   ```

3. **Create Installer** (Optional)
   - Use Inno Setup or NSIS to create installer
   - Include `dist\SendAnywhere\` folder

4. **Distribute**
   - Zip `dist\SendAnywhere\` folder
   - Or create installer package
