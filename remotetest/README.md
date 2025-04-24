# Windows RDP 远程访问配置指南

本项目使用GitHub Actions和Cloudflare Tunnel实现Windows远程桌面访问。不上传0

## Cloudflare配置步骤

1. 登录Cloudflare Zero Trust控制台 (https://dash.teams.cloudflare.com/)

2. 创建Tunnel:
   - 进入`Access > Tunnels`
   - 点击`Create a tunnel`
   - 输入Tunnel名称（例如：windows-rdp）
   - 保存生成的Tunnel Token

3. 配置GitHub Secrets:
   - 在GitHub仓库设置中找到`Secrets and variables > Actions`
   - 创建以下secrets:
     - `TUNNEL_TOKEN`: 设置为之前保存的Tunnel Token
     - `RDP_PASSWORD`: 设置远程桌面密码，必须满足以下要求：
     - 至少12个字符
     - 包含大写字母
     - 包含小写字母
     - 包含数字
     - 包含特殊字符

4. 配置Public Hostname:
   - 在Tunnel详情页面，点击`Configure`
   - 添加新的Public Hostname
   - 设置Subdomain（例如：rdp）
   - 选择你的Cloudflare域名
   - Service类型选择`TCP`
   - URL设置为`localhost:3389`
   - 保存配置

## 使用方法

1. 在GitHub Actions页面手动触发workflow
2. 等待workflow运行完成
3. 使用Windows远程桌面客户端连接
先要本地运行
cloudflared access rdp --hostname gitacrdp.你的域名 --url rdp://localhost:13389
   - 地址：localhost:13389
   - 用户名：runneradmin
   - 密码：使用你在GitHub Secrets中设置的RDP_PASSWORD

## 安全提示

- 定期更改访问密码
- 使用强密码策略
- 及时关闭不使用的Tunnel
- 定期检查访问日志