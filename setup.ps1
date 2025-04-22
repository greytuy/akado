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

# 主函数
function Main {
    try {
        Test-RequiredSecrets
        $cloudflaredPath = Install-Cloudflared
        Enable-RDPAccess
        Set-RDPPassword
        Start-CloudflareTunnel $cloudflaredPath

        Write-Host "设置完成！"
        Write-Host "远程桌面连接信息："
        Write-Host "用户名: runneradmin"
        Write-Host "密码: 请使用设置的RDP_PASSWORD"

        # 确保Cloudflare Tunnel服务在后台运行
        $tunnelService = Get-Service cloudflared
        if ($tunnelService.Status -ne 'Running') {
            throw "Cloudflare Tunnel服务未在运行"
        }
        Write-Host "Cloudflare Tunnel服务正在后台运行"
    }
    catch {
        Write-Error "设置过程中出现错误: $_"
        exit 1
    }
}

# 运行主函数
Main