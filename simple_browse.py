import asyncio
import random
import time
import sys
import io
import os
from typing import Optional, List, Dict

from playwright.async_api import async_playwright, Page, Browser
import requests

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 简化版配置
SIMPLE_CONFIG = {
    'scroll': {
        'min_speed': 500,  # 最小滚动速度(毫秒)
        'max_speed': 2000,  # 最大滚动速度
        'min_distance': 100,  # 最小滚动距离
        'max_distance': 300,  # 最大滚动距离
        'pause_chance': 0.15,  # 暂停概率
        'min_pause': 2000,  # 最小暂停时间(毫秒)
        'max_pause': 5000,  # 最大暂停时间
    },
    'time': {
        'browse_time': 1800000,  # 浏览时间(毫秒) - 30分钟
        'rest_time': 300000,  # 休息时间 - 5分钟
    },
    'article': {
        'topic_list_limit': 50,  # 话题列表限制
        'like_chance': 0.3,  # 点赞概率
    },
    'login': {
        'username_field': '#login-account-name',
        'password_field': '#login-account-password',
        'login_button': '.login-button'
    }
}

class SimpleBrowseController:
    def __init__(self):
        self.page: Optional[Page] = None
        self.browser: Optional[Browser] = None
        self.is_scrolling = False
        self.auto_running = False
        self.accumulated_time = 0
        self.last_action_time = time.time() * 1000
        self.topic_list: List[Dict] = []
        self.likes_count = 0
        
    def log(self, message, level="INFO"):
        """输出日志信息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
        # 根据日志级别设置不同颜色
        level_colors = {
            "INFO": "\033[1;32m",  # 绿色
            "WARNING": "\033[1;33m",  # 黄色
            "ERROR": "\033[1;31m",  # 红色
            "DEBUG": "\033[1;36m"   # 青色
        }
        
        color = level_colors.get(level, "\033[0m")
        reset = "\033[0m"
        
        print(f"[{timestamp}] [{color}{level}{reset}] {message}")

    async def initialize(self):
        """初始化浏览器和页面"""
        self.log("开始初始化浏览器和页面", "INFO")
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True  # 无头模式运行
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        self.page.set_default_timeout(30000)
        self.log("浏览器和页面初始化完成", "INFO")
        
    async def login(self):
        """登录到网站"""
        self.log("准备登录", "INFO")
        
        # 获取环境变量中的用户名和密码
        username = os.environ.get('LINUX_DO_USERNAME')
        password = os.environ.get('LINUX_DO_PASSWORD')
        
        if not username or not password:
            self.log("未设置用户名或密码环境变量", "ERROR")
            return False
            
        try:
            # 访问登录页面
            await self.page.goto('https://linux.do/login')
            await asyncio.sleep(2)
            
            # 输入用户名和密码
            await self.page.fill(SIMPLE_CONFIG['login']['username_field'], username)
            await asyncio.sleep(1)
            await self.page.fill(SIMPLE_CONFIG['login']['password_field'], password)
            await asyncio.sleep(1)
            
            # 点击登录按钮
            await self.page.click(SIMPLE_CONFIG['login']['login_button'])
            
            # 等待登录完成，增加延时
            await asyncio.sleep(10)
            
            # 检查是否登录成功
            current_url = self.page.url
            if 'login' not in current_url:
                self.log("登录成功", "INFO")
                return True
            else:
                self.log("登录失败，等待5分钟以便人工干预", "WARNING")
                # 等待5分钟，允许人工干预登录
                self.log("请在5分钟内手动完成登录操作", "INFO")
                for i in range(5):
                    self.log(f"等待人工干预: 还剩 {5-i} 分钟", "INFO")
                    await asyncio.sleep(60)  # 等待1分钟
                    
                    # 再次检查是否已登录
                    current_url = self.page.url
                    if 'login' not in current_url:
                        self.log("检测到已成功登录", "INFO")
                        return True
                
                self.log("等待超时，登录失败", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"登录过程中出错: {e}", "ERROR")
            return False

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            self.log("正在关闭浏览器", "INFO")
            await self.browser.close()
            self.log("浏览器已关闭", "INFO")

    async def is_page_loaded(self) -> bool:
        """检查页面是否加载完成"""
        loading_elements = await self.page.query_selector_all('.loading, .infinite-scroll')
        return len(loading_elements) == 0

    async def is_near_bottom(self) -> bool:
        """检查是否接近页面底部"""
        return await self.page.evaluate("""
            () => {
                const {scrollHeight, clientHeight, scrollTop} = document.documentElement;
                return (scrollTop + clientHeight) >= (scrollHeight - 200);
            }
        """)

    async def get_latest_topics(self):
        """获取最新话题列表"""
        self.log("开始获取最新话题列表", "INFO")
        page = 1
        topic_list = []
        retry_count = 0

        while len(topic_list) < SIMPLE_CONFIG['article']['topic_list_limit'] and retry_count < 3:
            try:
                response = requests.get(
                    f"https://linux.do/latest.json?no_definitions=true&page={page}",
                    timeout=10
                )
                data = response.json()

                if data.get('topic_list', {}).get('topics'):
                    topic_list.extend(data['topic_list']['topics'])
                    page += 1
                else:
                    break
            except Exception as e:
                print(f'获取文章列表失败: {e}')
                retry_count += 1
                await asyncio.sleep(1)

        if len(topic_list) > SIMPLE_CONFIG['article']['topic_list_limit']:
            topic_list = topic_list[:SIMPLE_CONFIG['article']['topic_list_limit']]

        self.topic_list = topic_list
        self.log(f'已获取 {len(topic_list)} 篇文章', "INFO")

    async def get_next_topic(self):
        """获取下一个要浏览的话题"""
        if not self.topic_list:
            await self.get_latest_topics()

        if self.topic_list:
            return self.topic_list.pop(0)
        return None

    async def navigate_next_topic(self):
        """导航到下一个话题"""
        self.log("准备导航到下一个话题", "INFO")
        next_topic = await self.get_next_topic()
        if next_topic:
            title = next_topic.get('title', '未知标题')
            self.log(f"导航到新文章: {title}", "INFO")
            url = f"https://linux.do/t/topic/{next_topic['id']}"
            await self.page.goto(url)
            await asyncio.sleep(2)  # 等待页面加载
        else:
            self.log("没有更多文章，返回首页", "INFO")
            await self.page.goto("https://linux.do/latest")

    async def like_random_comment(self) -> bool:
        """随机点赞评论"""
        # 根据概率决定是否尝试点赞
        if random.random() > SIMPLE_CONFIG['article']['like_chance']:
            return False
            
        self.log("开始查找可点赞的评论", "INFO")
        # 获取所有可点赞按钮
        like_buttons = await self.page.query_selector_all(
            '.like-button:not(.has-like), .like-count:not(.liked), '
            '[data-like-button]:not(.has-like), .discourse-reactions-reaction-button:not(.reacted)'
        )

        # 过滤掉不可见的按钮
        visible_buttons = []
        for button in like_buttons:
            is_visible = await button.is_visible()
            if is_visible:
                visible_buttons.append(button)

        self.log(f"找到 {len(visible_buttons)} 个可见的点赞按钮", "INFO")

        if visible_buttons:
            # 随机选择一个按钮
            random_button = random.choice(visible_buttons)
            # 滚动到按钮位置
            await random_button.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            self.log("找到可点赞的评论，准备点赞", "INFO")
            await random_button.click()
            self.likes_count += 1
            self.log(f"点赞成功，当前已点赞数: {self.likes_count}", "INFO")
            await asyncio.sleep(1)
            return True

        return False

    async def start_scrolling(self):
        """开始滚动浏览"""
        if self.is_scrolling:
            return

        self.log("开始滚动浏览页面", "INFO")
        self.is_scrolling = True
        self.last_action_time = time.time() * 1000

        while self.is_scrolling and self.auto_running:
            # 随机滚动速度和距离
            speed = random.randint(SIMPLE_CONFIG['scroll']['min_speed'], SIMPLE_CONFIG['scroll']['max_speed'])
            distance = random.randint(SIMPLE_CONFIG['scroll']['min_distance'], SIMPLE_CONFIG['scroll']['max_distance'])
            
            # 执行滚动
            await self.page.evaluate(f'window.scrollBy(0, {distance})')
            
            # 随机暂停
            if random.random() < SIMPLE_CONFIG['scroll']['pause_chance']:
                pause_time = random.randint(
                    SIMPLE_CONFIG['scroll']['min_pause'],
                    SIMPLE_CONFIG['scroll']['max_pause']
                )
                self.log(f"随机暂停 {pause_time/1000} 秒", "INFO")
                await asyncio.sleep(pause_time/1000)  # 转换为秒
            
            # 检查是否到达页面底部
            if await self.is_near_bottom():
                await asyncio.sleep(1)
                
                if await self.is_near_bottom() and await self.is_page_loaded():
                    self.log("已到达页面底部，准备导航到下一篇文章", "INFO")
                    await asyncio.sleep(1)
                    
                    # 尝试点赞
                    await self.like_random_comment()
                    
                    # 导航到下一篇文章
                    await self.navigate_next_topic()
                    await asyncio.sleep(2)
            
            await asyncio.sleep(speed / 1000)  # 转换为秒
            await self.accumulate_time()

    async def accumulate_time(self):
        """累计浏览时间并处理休息"""
        now = time.time() * 1000
        elapsed = now - self.last_action_time
        self.accumulated_time += elapsed
        self.last_action_time = now
        
        browse_minutes = self.accumulated_time / 60000  # 转换为分钟
        total_minutes = SIMPLE_CONFIG['time']['browse_time'] / 60000
        
        if browse_minutes > 0 and browse_minutes % 5 == 0:  # 每5分钟显示一次
            self.log(f"累计浏览时间: {browse_minutes:.0f}/{total_minutes:.0f} 分钟", "INFO")

        if self.accumulated_time >= SIMPLE_CONFIG['time']['browse_time']:
            self.log(f"达到设定的浏览时间 {total_minutes:.0f} 分钟，准备休息", "INFO")
            self.accumulated_time = 0
            await self.pause_for_rest()

    async def pause_for_rest(self):
        """暂停休息"""
        self.is_scrolling = False
        rest_time_minutes = SIMPLE_CONFIG['time']['rest_time'] / 60000  # 转换为分钟
        self.log(f"开始休息 {rest_time_minutes:.0f} 分钟", "INFO")
        
        # 显示休息倒计时
        start_time = time.time()
        rest_time_seconds = SIMPLE_CONFIG['time']['rest_time'] / 1000
        
        while time.time() - start_time < rest_time_seconds:
            remaining = int(rest_time_seconds - (time.time() - start_time))
            minutes = remaining // 60
            seconds = remaining % 60
            
            if remaining % 30 == 0:  # 每30秒显示一次
                self.log(f"休息倒计时: {minutes:02d}:{seconds:02d}", "INFO")
                
            await asyncio.sleep(1)
            
        self.log("休息结束，准备继续浏览", "INFO")
        await self.start_scrolling()

    def stop_scrolling(self):
        """停止滚动"""
        self.is_scrolling = False
        self.auto_running = False

    async def run(self):
        """运行浏览器自动化"""
        try:
            await self.initialize()

            # 首先登录
            login_success = await self.login()
            if not login_success:
                self.log("登录失败，程序退出", "ERROR")
                return
                
            # 设置自动运行标志
            self.auto_running = True

            # 获取话题列表并开始浏览
            await self.get_latest_topics()
            await self.navigate_next_topic()
            await self.start_scrolling()

            # 保持运行直到手动停止
            while self.auto_running:
                await asyncio.sleep(1)

        except Exception as e:
            self.log(f"运行出错: {e}", "ERROR")
        finally:
            await self.close()

async def main():
    controller = SimpleBrowseController()
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())