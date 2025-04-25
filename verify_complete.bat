@echo off
echo Marking Cloudflare verification as complete...
python -c "from cloudflare_handler import mark_verification_complete; mark_verification_complete()"
echo.
echo Verification has been marked as complete! The program will continue.
echo.
timeout /t 5