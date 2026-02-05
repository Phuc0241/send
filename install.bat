@echo off
echo ========================================
echo Installing Dependencies for Send Anywhere
echo ========================================
cd /d C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python
C:\Users\PHUC\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
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
