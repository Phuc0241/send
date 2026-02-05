@echo off
echo ========================================
echo Building Send Anywhere Executable
echo ========================================
echo.

cd /d C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python

echo [1/3] Installing PyInstaller...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install pyinstaller

echo.
echo [2/3] Building executable...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m PyInstaller build_config.spec --clean

echo.
echo [3/3] Build complete!
echo.
echo ========================================
echo Executable created in: dist\SendAnywhere\
echo ========================================
echo.
echo Run: dist\SendAnywhere\SendAnywhere.exe
echo.
pause
