@echo off
echo 正在标记Cloudflare验证已完成...
python -c "from cloudflare_handler import mark_verification_complete; mark_verification_complete()"
echo.
echo 验证已标记为完成！程序将继续执行。
echo.
timeout /t 5