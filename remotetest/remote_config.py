# 远程调试配置
REMOTE_CONFIG = {
    'debug': {
        'enabled': True,
        'host': 'localhost',
        'port': 9222,
        'headless': False,
        'slowMo': 100,  # 调试时放慢操作速度（毫秒）
        'devtools': True,  # 自动打开开发者工具
    },
    'cloudflare': {
        'tunnel_hostname': 'rdp.example.com',  # 替换为你的Cloudflare Tunnel域名
        'rdp_port': 3389,
        'local_port': 9222,
    },
    'browser': {
        'width': 1280,
        'height': 800,
        'viewport': {
            'width': 1280,
            'height': 800,
        },
    },
}