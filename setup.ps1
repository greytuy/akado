# 下载并设置Cloudflared
$ErrorActionPreference = "Stop"

# 验证环境变量
function Test-RequiredSecrets {
    if (-not $env:TUNNEL_TOKEN -or -not $env:RDP_PASSWORD) {
        throw "缺少必要的环境变量 TUNNEL_TOKEN 或 RDP_PASSWORD"
    }
}

# 验证密码复杂度
function Test-PasswordComplexity {
    param($Password)
    if ($Password.Length -lt 12 -or 
        -not ($Password -match '[A-Z]') -or 
        -not ($Password -match '[a-z]') -or 
        -not ($Password -match '\d') -or 
        -not ($Password -match '[^A-Za-z0-9]')) {
        throw "密码必须至少包含12个字符，并包含大小写字母、数字和特殊字符"
    }
}

# 下载Cloudflared
function Install-Cloudflared {
    try {
        $cloudflaredPath = "$PWD\cloudflared.exe"
        Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $cloudflaredPath
        # 验证cloudflared可执行文件
        if (-not (Test-Path $cloudflaredPath)) {
            throw "Cloudflared可执行文件不存在"
        }
        $version = & $cloudflaredPath --version 2>&1
        Write-Host "Cloudflared版本: $version"
        return $cloudflaredPath
    }
    catch {
        throw "下载Cloudflared失败: $_"
    }
}

# 配置RDP访问
function Enable-RDPAccess {
    try {
        Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name 'fDenyTSConnections' -Value 0
        Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'
        Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'UserAuthentication' -Value 1
    }
    catch {
        throw "配置RDP访问失败: $_"
    }
}

# 设置RDP密码
function Set-RDPPassword {
    try {
        Test-PasswordComplexity $env:RDP_PASSWORD
        $SecurePassword = ConvertTo-SecureString $env:RDP_PASSWORD -AsPlainText -Force
        Set-LocalUser -Name "runneradmin" -Password $SecurePassword
        Write-Host "RDP密码设置完成"
    }
    catch {
        throw "设置RDP密码失败: $_"
    }
}

# 启动Cloudflare Tunnel
function Start-CloudflareTunnel {
    param($CloudflaredPath)
    try {
        if (-not ($env:TUNNEL_TOKEN -match '^eyJ')) {
            throw "Tunnel Token格式无效"
        }

        Write-Host "正在安装Cloudflare Tunnel服务..."
        $result = Start-Process -FilePath $CloudflaredPath -ArgumentList "service", "install", $env:TUNNEL_TOKEN -Wait -NoNewWindow -PassThru
        if ($result.ExitCode -ne 0) {
            throw "Cloudflare Tunnel服务安装失败，退出代码: $($result.ExitCode)"
        }

        Start-Sleep -Seconds 5
        Start-Service cloudflared
        if (-not $?) {
            throw "Cloudflare Tunnel服务启动失败"
        }
        Write-Host "Cloudflare Tunnel服务已启动"
    }
    catch {
        throw "启动Cloudflare Tunnel失败: $_"
    }
}

# 准备自动浏览环境
function Prepare-AutoBrowseEnvironment {
    try {
        # 确保批处理脚本在当前目录
        if (-not (Test-Path ".\start_browse.bat")) {
            Write-Host "未找到start_browse.bat，创建默认脚本..."
            @"
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
"@ | Set-Content -Path ".\start_browse.bat"
        }

        if (-not (Test-Path ".\verify_complete.bat")) {
            Write-Host "未找到verify_complete.bat，创建默认脚本..."
            @"
@echo off
echo 正在标记Cloudflare验证已完成...
python -c "from cloudflare_handler import mark_verification_complete; mark_verification_complete()"
echo.
echo 验证已标记为完成！程序将继续执行。
echo.
timeout /t 5
"@ | Set-Content -Path ".\verify_complete.bat"
        }

        # 创建使用说明文件
        @"
# Linux.do自动浏览工具 - 远程使用说明

## 快速开始

1. 双击桌面上的 **start_browse.bat** 启动自动浏览工具
2. 如果遇到Cloudflare验证页面，手动完成验证
3. 验证完成后，双击桌面上的 **verify_complete.bat** 通知程序继续执行
4. 程序会自动继续运行，包括5分钟的手动登录时间

## 功能说明

- **CDP伪装**: 自动通过Chrome DevTools Protocol修改navigator.webdriver属性
- **随机滑动**: 模拟真实用户的浏览行为，包含随机停顿时间
- **登录延时**: 提供5分钟时间让您手动登录和操作网站

## 注意事项

- 请勿关闭浏览器窗口或命令提示符窗口
- 运行过程中会产生日志文件，帮助排查问题
- 程序设计为模拟真实用户行为，包含随机暂停和休息

"@ | Set-Content -Path ".\README.md"

        # 复制到桌面
        Write-Host "正在复制工具脚本到桌面..."
        $desktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
        Copy-Item -Path ".\start_browse.bat" -Destination "$desktopPath\start_browse.bat" -Force
        Copy-Item -Path ".\verify_complete.bat" -Destination "$desktopPath\verify_complete.bat" -Force
        Copy-Item -Path ".\README.md" -Destination "$desktopPath\Linux.do自动浏览说明.md" -Force

        # 创建快捷方式
        $WshShell = New-Object -ComObject WScript.Shell
        $shortcut = $WshShell.CreateShortcut("$desktopPath\启动Linux.do自动浏览.lnk")
        $shortcut.TargetPath = "cmd.exe"
        $shortcut.Arguments = "/c `"$PWD\start_browse.bat`""
        $shortcut.WorkingDirectory = $PWD
        $shortcut.Description = "启动Linux.do自动浏览工具"
        $shortcut.IconLocation = "C:\Windows\System32\SHELL32.dll,44"
        $shortcut.Save()

        Write-Host "自动浏览环境准备完成！脚本已复制到桌面。"
    }
    catch {
        Write-Warning "准备自动浏览环境时出错: $_"
        # 继续执行，不影响主流程
    }
}

# 主函数
function Main {
    try {
        Test-RequiredSecrets
        $cloudflaredPath = Install-Cloudflared
        Enable-RDPAccess
        Set-RDPPassword
        Start-CloudflareTunnel $cloudflaredPath
        
        # 准备自动浏览环境
        Prepare-AutoBrowseEnvironment

        Write-Host "设置完成！"
        Write-Host "远程桌面连接信息："
        Write-Host "用户名: runneradmin"
        Write-Host "密码: 请使用设置的RDP_PASSWORD"
        Write-Host ""
        Write-Host "请使用RDP客户端连接到您的Cloudflare Tunnel域名"
        Write-Host "连接后，在桌面上双击'启动Linux.do自动浏览'快捷方式开始运行"

        # 循环检测Cloudflare Tunnel服务状态
        $endTime = (Get-Date).AddMinutes(120)  # 设置为2小时，可以根据需要调整
        while ((Get-Date) -lt $endTime) {
            $tunnelService = Get-Service cloudflared -ErrorAction SilentlyContinue
            if ($null -eq $tunnelService -or $tunnelService.Status -ne 'Running') {
                Write-Warning "Cloudflare Tunnel服务未在运行，尝试重启..."
                Start-Service cloudflared -ErrorAction SilentlyContinue
            } else {
                Write-Host "Cloudflare Tunnel服务正在后台运行 [$(Get-Date)]"
            }
            Start-Sleep -Seconds 60
        }
    }
    catch {
        Write-Error "设置过程中出现错误: $_"
        exit 1
    }
}

# 运行主函数
Main
