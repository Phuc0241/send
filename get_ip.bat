@echo off
echo ========================================
echo Getting Your IP Address
echo ========================================
echo.
ipconfig | findstr /i "IPv4"
echo.
echo ========================================
echo Use this IP to access from other devices
echo ========================================
echo.
echo Example:
echo   http://YOUR_IP:5000
echo.
pause
