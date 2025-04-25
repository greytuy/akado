@echo off
echo ===================================
echo   Linux.do 自动浏览工具启动程序
echo ===================================
echo.
echo 正在启动自动浏览程序...
echo 如果遇到Cloudflare验证，请手动完成验证后运行桌面上的verify_complete.bat
echo.

rem 设置环境变量标记为远程会话
set REMOTE_SESSION=true

rem 启动主程序
python main.py

echo.
echo 程序已结束运行，按任意键退出
pause > nul