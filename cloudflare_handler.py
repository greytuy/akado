import asyncio
import os
import time
import json
from pathlib import Path

class CloudflareRemoteHandler:
    """远程Cloudflare验证处理器"""
    
    def __init__(self, status_file_path="./cloudflare_status.json"):
        """初始化处理器
        
        Args:
            status_file_path: 状态文件路径，用于与远程RDP会话通信
        """
        self.status_file_path = status_file_path
        self.is_remote_session = os.environ.get("REMOTE_SESSION") == "true"
    
    def _create_status_file(self, status="waiting", message=""):
        """创建或更新状态文件"""
        status_data = {
            "status": status,
            "timestamp": time.time(),
            "message": message,
            "verification_complete": status == "complete"
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(self.status_file_path)), exist_ok=True)
        
        with open(self.status_file_path, "w") as f:
            json.dump(status_data, f)
    
    def _read_status_file(self):
        """读取状态文件"""
        if not Path(self.status_file_path).exists():
            return {"status": "not_found"}
            
        try:
            with open(self.status_file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"status": "error"}
    
    async def wait_for_verification(self, timeout=1800):  # 默认等待30分钟
        """等待远程验证完成
        
        Args:
            timeout: 最大等待时间（秒）
            
        Returns:
            bool: 验证是否成功完成
        """
        # 创建等待验证的状态文件
        self._create_status_file(status="waiting", message="等待远程RDP验证Cloudflare")
        
        # 显示等待消息并创建验证说明文件
        self._create_verification_instructions()
        print(f"\n[通知] 等待Cloudflare验证 - 请手动完成验证，然后运行 verify_complete.bat")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_data = self._read_status_file()
            
            if status_data.get("status") == "complete":
                print("\n[通知] Cloudflare验证已完成，继续执行")
                return True
                
            # 每5秒打印一次状态
            if (int(time.time() - start_time) % 5) == 0:
                remaining = int(timeout - (time.time() - start_time))
                print(f"\r等待远程验证，剩余时间: {remaining // 60}分{remaining % 60}秒", end="")
                
            await asyncio.sleep(1)
        
        print("\n[错误] 验证超时，无法继续执行")
        return False
    
    def mark_verification_complete(self):
        """标记验证已完成（从RDP会话中调用）"""
        self._create_status_file(status="complete", message="远程验证已完成")
        print("已标记Cloudflare验证为已完成")
    
    def _create_verification_instructions(self):
        """创建验证说明文件"""
        instructions = """
# Cloudflare验证说明

## 当您在浏览器中看到Cloudflare验证页面时:

1. 手动完成验证步骤（通常是点击checkbox或完成拼图验证）
2. 验证通过后，运行桌面上的 `verify_complete.bat` 脚本
3. 浏览器会自动继续执行后续操作

注意: 请不要关闭浏览器窗口，让程序保持运行

"""
        with open("cloudflare_instructions.md", "w") as f:
            f.write(instructions)
        
        # 尝试复制到桌面
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.exists(desktop_path):
                desktop_file = os.path.join(desktop_path, "cloudflare_instructions.md")
                with open(desktop_file, "w") as f:
                    f.write(instructions)
        except:
            pass  # 如果无法写入桌面，就忽略错误

# 用于RDP会话中手动标记验证完成的辅助函数
def mark_verification_complete(status_file_path="./cloudflare_status.json"):
    handler = CloudflareRemoteHandler(status_file_path)
    handler.mark_verification_complete()
    
if __name__ == "__main__":
    # 如果直接运行此脚本，则标记验证完成
    import sys
    if len(sys.argv) > 1:
        mark_verification_complete(sys.argv[1])
    else:
        mark_verification_complete()