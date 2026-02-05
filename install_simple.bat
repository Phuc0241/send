@echo off
echo ========================================
echo Installing Send Anywhere Dependencies
echo (Using latest compatible versions)
echo ========================================
cd /d C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python

echo.
echo Installing FastAPI and Uvicorn...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install fastapi uvicorn[standard] --upgrade

echo.
echo Installing WebSockets...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install websockets --upgrade

echo.
echo Installing aiohttp...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install aiohttp --upgrade

echo.
echo Installing other dependencies...
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install python-multipart tqdm aiofiles --upgrade

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Now you can run:
echo   - start_relay.bat
echo   - start_signaling.bat
echo   - start_web.bat
echo.
pause
