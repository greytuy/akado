import os
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from main import BrowseController

async def main():
    # 设置远程调试环境变量
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'  # 强制在本地安装浏览器
    os.environ['PWDEBUG'] = '1'  # 启用Playwright调试器

    # 初始化并运行浏览控制器
    controller = BrowseController()
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())