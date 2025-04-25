@echo off
echo ===================================
echo   Linux.do Auto Browsing Tool
echo ===================================
echo.
echo Starting auto browsing program...
echo If you encounter Cloudflare verification, please complete it manually and then run verify_complete.bat on the desktop
echo.

rem Set environment variable flag for remote session
set REMOTE_SESSION=true

rem Start main program
python main.py

echo.
echo Program has finished running, press any key to exit
pause > nul