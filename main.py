import asyncio
import random
import time
import sys
import io
from typing import Optional, List, Dict
import os

from playwright.async_api import async_playwright, Page, Browser
import requests

from config import CONFIG

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class BrowseController:
    def __init__(self):
        self.page: Optional[Page] = None
        self.browser: Optional[Browser] = None
        self.is_scrolling = False
        self.auto_running = False
        self.accumulated_time = 0
        self.last_action_time = time.time() * 1000
        self.topic_list: List[Dict] = []
        self.first_use_checked = False
        self.likes_count = 0
        self.selected_post = None
        self.debug = CONFIG.get('debug', False)  # 从配置中获取debug模式设置
        
    def log(self, message, level="INFO"):
        """输出日志信息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if level == "DEBUG" and not self.debug:
            return
            
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
        
        # 设置基本的浏览器启动参数
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--window-size=1920,1080',
            '--start-maximized'
        ]
        
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=browser_args
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
        # 使用CDP方法修改属性 - 这是主要的解决方案
        self.log("使用CDP修改navigator属性", "INFO")
        await self.page.add_init_script("""
            // 使用CDP修改navigator.webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # 设置默认超时时间
        self.page.set_default_timeout(30000)
        self.log("浏览器和页面初始化完成", "INFO")
        if self.debug:
            self.log("CDP属性修改已应用", "DEBUG")
        
    async def check_cloudflare(self) -> bool:
        """检查是否遇到Cloudflare验证"""
        try:
            self.log("检查是否存在Cloudflare验证", "DEBUG")
            cloudflare_element = await self.page.query_selector('iframe[title*="challenge"], #challenge-stage, #cf-challenge-running')
            result = cloudflare_element is not None
            if result:
                self.log("检测到Cloudflare验证元素", "DEBUG")
            return result
        except Exception as e:
            self.log(f"检查Cloudflare验证时出错: {e}", "ERROR")
            return False
            
    async def wait_for_cloudflare(self, max_retries: int = 3) -> bool:
        """等待并处理Cloudflare验证"""
        # 检查是否在GitHub Actions环境中运行
        is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                if await self.check_cloudflare():
                    self.log(f'检测到Cloudflare验证，第{retry_count + 1}次尝试绕过...', "WARNING")
                    
                    # 如果在GitHub Actions环境中，使用远程验证处理
                    if is_github_action:
                        self.log("在GitHub Actions环境中检测到Cloudflare验证，等待远程RDP验证", "WARNING")
                        
                        # 导入远程验证处理模块
                        try:
                            from remotetest.cloudflare_handler import CloudflareRemoteHandler
                            remote_handler = CloudflareRemoteHandler()
                            
                            # 等待远程验证完成
                            verification_success = await remote_handler.wait_for_verification()
                            if verification_success:
                                self.log("远程验证成功完成", "INFO")
                                # 等待页面加载
                                await asyncio.sleep(3)
                                if not await self.check_cloudflare():
                                    return True
                                else:
                                    self.log("验证后仍检测到Cloudflare验证，继续尝试", "WARNING")
                            else:
                                self.log("远程验证超时或失败", "ERROR")
                                return False
                        except ImportError:
                            self.log("无法导入远程验证处理模块，回退到标准处理流程", "ERROR")
                    
                    # 非GitHub Actions环境下的标准处理流程（保持原有逻辑）
                    # 显示美化的选择菜单
                    self.log("显示Cloudflare验证选择菜单", "DEBUG")
                    print("\n" + "="*70)
                    print("\033[1;36m╔════════════════════════════════════════════════════════════╗\033[0m")
                    print("\033[1;36m║                                                            ║\033[0m")
                    print("\033[1;36m║              \033[1;33mCloudflare 验证选择菜单\033[1;36m               ║\033[0m")
                    print("\033[1;36m║                                                            ║\033[0m")
                    print("\033[1;36m╚════════════════════════════════════════════════════════════╝\033[0m")
                    print("="*70)
                    
                    print("\033[1;35m┌─ 可用选项 ───────────────────────────────────────────────┐\033[0m")
                    print("\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m")
                    print("\033[1;35m│\033[0m  \033[1;33m[1]\033[0m \033[1m远程手动绕过\033[0m - 您需要手动完成验证                \033[1;35m│\033[0m")
                    print("\033[1;35m│\033[0m  \033[1;33m[2]\033[0m \033[1m自动尝试绕过\033[0m - 系统将尝试自动完成验证            \033[1;35m│\033[0m")
                    print("\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m")
                    print("\033[1;35m└─────────────────────────────────────────────────────────┘\033[0m")
                    print("="*70)
                    
                    print("\033[1;32m┌─ 提示信息 ───────────────────────────────────────────────┐\033[0m")
                    print("\033[1;32m│\033[0m  您有5分钟时间做出选择，超时将默认尝试自动绕过              \033[1;32m│\033[0m")
                    print("\033[1;32m└─────────────────────────────────────────────────────────┘\033[0m\n")
                    
                    # 设置5分钟超时
                    choice = None
                    timeout = 300  # 5分钟 = 300秒
                    start_time = time.time()
                    
                    # 使用异步方式等待用户输入，带超时
                    while time.time() - start_time < timeout and choice not in ['1', '2']:
                        remaining = int(timeout - (time.time() - start_time))
                        print(f'\r\033[1;34m剩余选择时间: {remaining}秒\033[0m', end='')
                        await asyncio.sleep(1)
                        
                        # 非阻塞方式检查是否有输入
                        import msvcrt
                        if msvcrt.kbhit():
                            key = msvcrt.getch().decode('utf-8')
                            if key in ['1', '2']:
                                choice = key
                                print()  # 换行
                                self.log(f"用户选择了选项 {choice}", "DEBUG")
                    
                    print()  # 换行
                    
                    # 根据选择或超时默认值处理验证
                    if choice == '1' or choice is None:
                        if choice is None:
                            self.log('选择超时，默认尝试自动绕过...', "WARNING")
                            # 等待一段时间，看是否能自动通过
                            await asyncio.sleep(10)
                            
                            # 如果自动绕过失败，切换到手动模式
                            if await self.check_cloudflare():
                                self.log('自动绕过失败，切换到手动模式...', "WARNING")
                                print('\n' + '='*50)
                                print('\033[1;31m自动绕过失败，请手动完成验证后按回车继续...\033[0m')
                                print('='*50)
                                input()
                                self.log("用户已确认手动验证完成", "DEBUG")
                        else:
                            self.log('用户选择了远程手动绕过', "INFO")
                            print('\n' + '='*50)
                            print('\033[1;33m请手动完成验证后按回车继续...\033[0m')
                            print('='*50)
                            input()
                            self.log("用户已确认手动验证完成", "DEBUG")
                        
                        await asyncio.sleep(2)
                        
                        # 验证完成后，检查页面是否正常
                        if not await self.check_cloudflare():
                            self.log('验证通过，询问用户是否开始自动浏览', "INFO")
                            if self.debug:
                                self.log('页面验证状态: 已通过', "DEBUG")
                                
                            # 美化的验证成功提示
                            print('\n' + '='*70)
                            print('\033[1;32m╔════════════════════════════════════════════════════════════╗\033[0m')
                            print('\033[1;32m║                                                            ║\033[0m')
                            print('\033[1;32m║                  验证通过！继续操作                        ║\033[0m')
                            print('\033[1;32m║                                                            ║\033[0m')
                            print('\033[1;32m╚════════════════════════════════════════════════════════════╝\033[0m')
                            print('='*70)
                            
                            print('\033[1;35m┌─ 请选择下一步操作 ─────────────────────────────────────────┐\033[0m')
                            print('\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m  \033[1;33m[Y]\033[0m - 开始自动浏览                                   \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m  \033[1;33m[N]\033[0m - 退出程序                                       \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m')
                            print('\033[1;35m└─────────────────────────────────────────────────────────┘\033[0m')
                            
                            start_browse = input('\n\033[1;37m请输入选择 (y/n): \033[0m').strip().lower()
                            if start_browse == 'y':
                                self.log('用户选择开始自动浏览', "INFO")
                                print('\n\033[1;32m开始自动浏览...\033[0m')
                                return True
                            else:
                                self.log('用户取消自动浏览，程序退出', "WARNING")
                                print('\n\033[1;31m用户取消自动浏览，程序退出\033[0m')
                                return False
                    elif choice == '2':
                        self.log('用户选择了自动尝试绕过', "INFO")
                        print('\n\033[1;36m您选择了自动尝试绕过，正在尝试...\033[0m')
                        # 等待一段时间，看是否能自动通过
                        await asyncio.sleep(10)
                        
                        # 如果自动绕过失败，询问是否切换到手动模式
                        if await self.check_cloudflare():
                            self.log('自动绕过失败，询问是否切换到手动模式', "WARNING")
                            print('\n' + '='*50)
                            print('\033[1;31m自动绕过失败\033[0m')
                            print('\033[1;33m是否切换到手动模式？\033[0m')
                            print('\033[1;33m[Y]\033[0m - 切换到手动模式')
                            print('\033[1;33m[N]\033[0m - 继续尝试自动绕过')
                            print('='*50)
                            switch_to_manual = input('请输入选择 (y/n): ').strip().lower()
                            if switch_to_manual == 'y':
                                self.log('用户选择切换到手动模式', "INFO")
                                print('\n' + '='*50)
                                print('\033[1;33m请手动完成验证后按回车继续...\033[0m')
                                print('='*50)
                                input()
                                self.log("用户已确认手动验证完成", "DEBUG")
                                await asyncio.sleep(2)
                                
                                # 验证完成后，检查页面是否正常
                                if not await self.check_cloudflare():
                                    self.log('验证通过，询问用户是否开始自动浏览', "INFO")
                                    print('\n' + '='*50)
                                    print('\033[1;32m验证通过！是否开始自动浏览？\033[0m')
                                    print('\033[1;33m[Y]\033[0m - 开始自动浏览')
                                    print('\033[1;33m[N]\033[0m - 退出程序')
                                    print('='*50)
                                    start_browse = input('请输入选择 (y/n): ').strip().lower()
                                    if start_browse == 'y':
                                        self.log('用户选择开始自动浏览', "INFO")
                                        print('\n\033[1;32m开始自动浏览...\033[0m')
                                        return True
                                    else:
                                        self.log('用户取消自动浏览，程序退出', "WARNING")
                                        print('\n\033[1;31m用户取消自动浏览，程序退出\033[0m')
                                        return False
                            else:
                                self.log('用户取消手动验证，尝试下一次自动绕过', "INFO")
                                print('\n\033[1;33m用户取消手动验证，尝试下一次自动绕过\033[0m')
                        else:
                            # 自动绕过成功
                            self.log('自动绕过成功，询问用户是否开始自动浏览', "INFO")
                            if self.debug:
                                self.log('自动绕过详情: Cloudflare验证已自动完成', "DEBUG")
                                
                            # 美化的自动绕过成功提示
                            print('\n' + '='*70)
                            print('\033[1;32m╔════════════════════════════════════════════════════════════╗\033[0m')
                            print('\033[1;32m║                                                            ║\033[0m')
                            print('\033[1;32m║                自动绕过成功！继续操作                      ║\033[0m')
                            print('\033[1;32m║                                                            ║\033[0m')
                            print('\033[1;32m╚════════════════════════════════════════════════════════════╝\033[0m')
                            print('='*70)
                            
                            print('\033[1;35m┌─ 请选择下一步操作 ─────────────────────────────────────────┐\033[0m')
                            print('\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m  \033[1;33m[Y]\033[0m - 开始自动浏览                                   \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m  \033[1;33m[N]\033[0m - 退出程序                                       \033[1;35m│\033[0m')
                            print('\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m')
                            print('\033[1;35m└─────────────────────────────────────────────────────────┘\033[0m')
                            
                            start_browse = input('\n\033[1;37m请输入选择 (y/n): \033[0m').strip().lower()
                            if start_browse == 'y':
                                self.log('用户选择开始自动浏览', "INFO")
                                print('\n\033[1;32m开始自动浏览...\033[0m')
                                return True
                            else:
                                self.log('用户取消自动浏览，程序退出', "WARNING")
                                print('\n\033[1;31m用户取消自动浏览，程序退出\033[0m')
                                return False
                else:
                    # 没有检测到Cloudflare验证，直接返回成功
                    self.log('没有检测到Cloudflare验证，直接返回成功', "DEBUG")
                    return True
                    
            except Exception as e:
                self.log(f'处理Cloudflare验证时出错: {e}', "ERROR")
                if self.debug:
                    import traceback
                    self.log(f'错误详情: {traceback.format_exc()}', "DEBUG")
                
            retry_count += 1
            await asyncio.sleep(2)
            
        self.log('达到最大重试次数，无法绕过Cloudflare验证', "ERROR")
        print('\n\033[1;31m达到最大重试次数，无法绕过Cloudflare验证\033[0m')
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

        while len(topic_list) < CONFIG['article']['topic_list_limit'] and retry_count < CONFIG['article']['retry_limit']:
            try:
                response = requests.get(
                    f"https://linux.do/latest.json?no_definitions=true&page={page}",
                    timeout=10
                )
                data = response.json()

                if data.get('topic_list', {}).get('topics'):
                    filtered_topics = [
                        topic for topic in data['topic_list']['topics']
                        if topic.get('posts_count', 0) < CONFIG['article']['comment_limit']
                    ]
                    topic_list.extend(filtered_topics)
                    page += 1
                else:
                    break
            except Exception as e:
                print(f'获取文章列表失败: {e}')
                retry_count += 1
                await asyncio.sleep(1)

        if len(topic_list) > CONFIG['article']['topic_list_limit']:
            topic_list = topic_list[:CONFIG['article']['topic_list_limit']]

        self.topic_list = topic_list
        self.log(f'已获取 {len(topic_list)} 篇文章', "INFO")
        if self.debug:
            self.log(f"文章列表详情: {[topic.get('title', '未知标题') for topic in topic_list[:5]]}...", "DEBUG")

    async def get_next_topic(self):
        """获取下一个要浏览的话题"""
        if not self.topic_list:
            await self.get_latest_topics()

        if self.topic_list:
            return self.topic_list.pop(0)
        return None

    async def navigate_next_topic(self):
        """导航到下一个话题"""
        self.log("准备导航到下一个话题", "DEBUG")
        next_topic = await self.get_next_topic()
        if next_topic:
            title = next_topic.get('title', '未知标题')
            self.log(f"导航到新文章: {title}", "INFO")
            print(f"\n\033[1;32m导航到新文章: {title}\033[0m")
            url = f"https://linux.do/t/topic/{next_topic['id']}"
            if next_topic.get('last_read_post_number'):
                url += f"/{next_topic['last_read_post_number']}"
            self.log(f"正在访问URL: {url}", "DEBUG")
            await self.page.goto(url)
            await asyncio.sleep(2)  # 等待页面加载
        else:
            self.log("没有更多文章，返回首页", "INFO")
            print("\n\033[1;33m没有更多文章，返回首页\033[0m")
            await self.page.goto("https://linux.do/latest")

    async def like_random_comment(self) -> bool:
        """随机点赞评论"""
        if not self.auto_running:
            self.log("自动运行已停止，取消点赞操作", "DEBUG")
            return False

        self.log("开始查找可点赞的评论", "DEBUG")
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

        self.log(f"找到 {len(visible_buttons)} 个可见的点赞按钮", "DEBUG")

        if visible_buttons:
            # 随机选择一个按钮
            random_button = random.choice(visible_buttons)
            # 滚动到按钮位置
            self.log("滚动到点赞按钮位置", "DEBUG")
            await random_button.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            if not self.auto_running:
                self.log("自动运行已停止，取消点赞操作", "DEBUG")
                return False

            self.log("找到可点赞的评论，准备点赞", "INFO")
            print('\033[1;32m找到可点赞的评论，准备点赞\033[0m')
            await random_button.click()
            self.likes_count += 1
            self.log(f"点赞成功，当前已点赞数: {self.likes_count}", "INFO")
            await asyncio.sleep(1)
            return True

        # 如果找不到可点赞的按钮，往下滚动
        self.log("当前位置没有找到可点赞的评论，往下滚动", "DEBUG")
        await self.page.evaluate('window.scrollBy(0, 500)')
        await asyncio.sleep(1)

        self.log("当前位置没有找到可点赞的评论，继续往下找", "INFO")
        print('\033[1;33m当前位置没有找到可点赞的评论，继续往下找\033[0m')
        return False

    async def handle_first_use(self):
        """处理首次使用的必读文章"""
        if not self.auto_running:
            self.log("自动运行已停止，取消首次使用处理", "DEBUG")
            return

        # 如果还没有选择文章
        if not self.selected_post:
            # 随机选择一篇必读文章
            self.selected_post = random.choice(CONFIG['must_read']['posts'])
            self.log(f'随机选择必读文章: {self.selected_post["url"]}', "INFO")
            print(f'\033[1;36m随机选择必读文章: {self.selected_post["url"]}\033[0m')
            await self.page.goto(self.selected_post['url'])
            await asyncio.sleep(2)
            return

        current_url = self.page.url
        self.log(f"当前URL: {current_url}", "DEBUG")

        # 如果在选中的文章页面
        if self.selected_post['url'] in current_url:
            self.log(f'当前在选中的文章页面，已点赞数: {self.likes_count}/{CONFIG["must_read"]["likes_needed"]}', "INFO")
            print(f'\033[1;32m当前在选中的文章页面，已点赞数: {self.likes_count}/{CONFIG["must_read"]["likes_needed"]}\033[0m')

            while self.likes_count < CONFIG['must_read']['likes_needed'] and self.auto_running:
                # 尝试点赞随机评论
                self.log("尝试点赞随机评论", "DEBUG")
                success = await self.like_random_comment()
                if success and self.likes_count >= CONFIG['must_read']['likes_needed']:
                    self.log('完成所需点赞数量，开始正常浏览', "INFO")
                    print('\033[1;32m完成所需点赞数量，开始正常浏览\033[0m')
                    self.first_use_checked = True
                    await self.get_latest_topics()
                    await self.navigate_next_topic()
                    break

                await asyncio.sleep(1)
        else:
            # 如果不在选中的文章页面，导航过去
            self.log(f"不在选中的文章页面，正在导航到: {self.selected_post['url']}", "INFO")
            print(f"\033[1;33m不在选中的文章页面，正在导航到必读文章...\033[0m")
            await self.page.goto(self.selected_post['url'])

    async def perform_random_scroll(self):
        """执行带有随机停顿时间的滚动"""
        self.log("执行随机滚动操作", "DEBUG")
        
        # 随机滚动距离
        distance = random.randint(CONFIG['scroll']['min_distance'], CONFIG['scroll']['max_distance'])
        
        # 随机滚动速度
        speed = random.randint(CONFIG['scroll']['min_speed'], CONFIG['scroll']['max_speed'])
        
        # 随机决定是否在滚动中间停顿
        should_pause = random.random() < 0.3  # 30%概率停顿
        
        # 执行滚动
        if should_pause:
            # 将滚动分成两半，中间停顿
            half_distance = distance / 2
            await self.page.evaluate(f'window.scrollBy(0, {half_distance})')
            
            # 随机停顿时间 (500ms - 2000ms)
            pause_time = random.randint(500, 2000)
            self.log(f"滚动停顿 {pause_time}ms", "DEBUG")
            await asyncio.sleep(pause_time / 1000)
            
            # 继续滚动
            await self.page.evaluate(f'window.scrollBy(0, {half_distance})')
        else:
            # 一次性滚动
            await self.page.evaluate(f'window.scrollBy(0, {distance})')
        
        # 滚动后等待
        await asyncio.sleep(speed / 1000)
        
        # 偶尔模拟鼠标悬停在内容上
        if random.random() < 0.15:  # 15%的概率
            try:
                # 寻找内容元素进行悬停
                content_elements = await self.page.query_selector_all('article, .post, .topic-body, p, h1, h2, h3, a')
                if content_elements:
                    random_element = random.choice(content_elements)
                    await random_element.hover()
                    hover_time = random.randint(800, 3000)
                    self.log(f"悬停在内容元素上 {hover_time}ms", "DEBUG")
                    await asyncio.sleep(hover_time / 1000)
            except Exception as e:
                self.log(f"模拟悬停时出错: {e}", "DEBUG")

    async def start_scrolling(self):
        """开始滚动浏览"""
        if self.is_scrolling:
            self.log("已经在滚动中，忽略此次调用", "DEBUG")
            return

        self.log("开始滚动浏览页面", "INFO")
        self.is_scrolling = True
        self.last_action_time = time.time() * 1000

        while self.is_scrolling:
            # 使用新的随机滚动方法
            await self.perform_random_scroll()
            
            # 检查是否达到页面底部
            if await self.is_near_bottom():
                await asyncio.sleep(0.8)

                if await self.is_near_bottom() and await self.is_page_loaded():
                    print("已到达页面底部，准备导航到下一篇文章...")
                    await asyncio.sleep(1)
                    await self.navigate_next_topic()
                    break

            await self.accumulate_time()

            # 随机快速滚动
            if random.random() < CONFIG['scroll']['fast_scroll_chance']:
                fast_scroll = random.randint(
                    CONFIG['scroll']['fast_scroll_min'],
                    CONFIG['scroll']['fast_scroll_max']
                )
                await self.page.evaluate(f'window.scrollBy(0, {fast_scroll})')
                await asyncio.sleep(0.2)

    async def accumulate_time(self):
        """累计浏览时间并处理休息"""
        now = time.time() * 1000
        elapsed = now - self.last_action_time
        self.accumulated_time += elapsed
        self.last_action_time = now
        
        if self.debug:
            browse_minutes = self.accumulated_time / 60000  # 转换为分钟
            total_minutes = CONFIG['time']['browse_time'] / 60000
            self.log(f"累计浏览时间: {browse_minutes:.2f}/{total_minutes:.2f} 分钟", "DEBUG")

        if self.accumulated_time >= CONFIG['time']['browse_time']:
            self.log(f"达到设定的浏览时间 {CONFIG['time']['browse_time']/60000:.2f} 分钟，准备休息", "INFO")
            self.accumulated_time = 0
            await self.pause_for_rest()

    async def pause_for_rest(self):
        """暂停休息"""
        self.is_scrolling = False
        rest_time_minutes = CONFIG['time']['rest_time'] / 60000  # 转换为分钟
        self.log(f"开始休息 {rest_time_minutes} 分钟", "INFO")
        print(f"\n\033[1;36m休息 {rest_time_minutes} 分钟...\033[0m")
        
        # 显示美化的休息菜单
        print("\n" + "="*60)
        print("\033[1;36m                休息时间到！\033[0m")
        print("="*60)
        print("\033[1;33m系统将自动暂停浏览活动，模拟真实用户行为\033[0m")
        if self.debug:
            self.log(f"休息时间设置为 {CONFIG['time']['rest_time']/1000} 秒", "DEBUG")
            self.log(f"当前已浏览时间: {self.accumulated_time/1000} 秒", "DEBUG")
        
        # 显示休息倒计时
        start_time = time.time()
        rest_time_seconds = CONFIG['time']['rest_time'] / 1000
        
        # 显示进度条
        bar_length = 40
        while time.time() - start_time < rest_time_seconds:
            remaining = int(rest_time_seconds - (time.time() - start_time))
            minutes = remaining // 60
            seconds = remaining % 60
            
            # 计算进度条
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / rest_time_seconds)
            bar_filled = int(bar_length * progress)
            bar_empty = bar_length - bar_filled
            
            # 显示彩色进度条和倒计时
            print(f"\r\033[1;34m休息倒计时: {minutes:02d}:{seconds:02d} [\033[1;32m{'█' * bar_filled}\033[1;30m{'░' * bar_empty}\033[1;34m] {int(progress*100)}%\033[0m", end="")
            await asyncio.sleep(1)
            
        print()  # 换行
        self.log("休息结束，准备继续浏览", "INFO")
        
        # 显示美化的继续浏览提示
        print("\n" + "="*60)
        print("\033[1;32m                休息结束！\033[0m")
        print("="*60)
        print("\033[1;36m系统将继续自动浏览活动...\033[0m")
        print("="*60 + "\n")
        
        await self.start_scrolling()

    def stop_scrolling(self):
        """停止滚动"""
        self.is_scrolling = False
        self.auto_running = False

    async def run(self):
        """运行浏览器自动化"""
        try:
            await self.initialize()

            # 首先访问首页
            await self.page.goto('https://linux.do')
            await asyncio.sleep(2)
            
            # 检查是否遇到Cloudflare验证
            cloudflare_result = await self.wait_for_cloudflare()
            if not cloudflare_result:
                print('无法绕过Cloudflare验证，程序退出')
                return
            
            # 设置自动运行标志
            self.auto_running = True
            
            # 启动登录延时挂起功能，允许用户手动登录操作5分钟
            self.log("启动登录延时挂起功能，请手动完成登录", "INFO")
            await self.login_with_manual_interaction()

            # 检查是否需要处理必读文章
            if not self.first_use_checked:
                await self.handle_first_use()
            else:
                # 获取话题列表并开始浏览
                await self.get_latest_topics()
                await self.navigate_next_topic()
                await self.start_scrolling()

            # 保持运行直到手动停止
            while self.auto_running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"运行出错: {e}")
            if self.debug:
                import traceback
                self.log(f"错误详情: {traceback.format_exc()}", "DEBUG")
        finally:
            await self.close()

    async def login_with_manual_interaction(self):
        """允许用户手动登录并操作5分钟"""
        self.log("进入登录延时挂起状态，等待用户手动操作", "INFO")
        
        # 显示美化的登录提示
        print("\n" + "="*70)
        print("\033[1;36m╔════════════════════════════════════════════════════════════╗\033[0m")
        print("\033[1;36m║                                                            ║\033[0m")
        print("\033[1;36m║              \033[1;33m请在5分钟内完成登录操作\033[1;36m                 ║\033[0m")
        print("\033[1;36m║                                                            ║\033[0m")
        print("\033[1;36m╚════════════════════════════════════════════════════════════╝\033[0m")
        print("="*70)
        
        print("\033[1;32m┌─ 操作说明 ───────────────────────────────────────────────┐\033[0m")
        print("\033[1;32m│\033[0m  1. 请点击网页中的登录按钮，手动完成登录                   \033[1;32m│\033[0m")
        print("\033[1;32m│\033[0m  2. 登录后您可以自由操作页面进行一些交互                   \033[1;32m│\033[0m")
        print("\033[1;32m│\033[0m  3. 5分钟后系统将继续自动操作                             \033[1;32m│\033[0m")
        print("\033[1;32m└─────────────────────────────────────────────────────────┘\033[0m")
        
        # 设置5分钟倒计时
        manual_time = 5 * 60  # 5分钟 = 300秒
        start_time = time.time()
        
        # 显示进度条
        bar_length = 40
        try:
            while time.time() - start_time < manual_time:
                remaining = int(manual_time - (time.time() - start_time))
                minutes = remaining // 60
                seconds = remaining % 60
                
                # 计算进度条
                elapsed = time.time() - start_time
                progress = min(1.0, elapsed / manual_time)
                bar_filled = int(bar_length * progress)
                bar_empty = bar_length - bar_filled
                
                # 显示彩色进度条和倒计时
                print(f"\r\033[1;34m手动操作倒计时: {minutes:02d}:{seconds:02d} [\033[1;32m{'█' * bar_filled}\033[1;30m{'░' * bar_empty}\033[1;34m] {int(progress*100)}%\033[0m", end="")
                
                # 每秒更新一次
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            # 用户可以按Ctrl+C跳过等待
            print("\n\033[1;33m用户手动跳过等待\033[0m")
        
        print("\n\033[1;32m手动操作时间结束，恢复自动浏览\033[0m")
        self.log("手动操作时间结束，恢复自动浏览", "INFO")

async def main():
    # 显示美化的欢迎界面
    print("\n" + "="*70)
    print("\033[1;36m╔════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[1;36m║                                                            ║\033[0m")
    print("\033[1;36m║              \033[1;33mLinux.do 自动浏览工具 v1.0.0\033[1;36m              ║\033[0m")
    print("\033[1;36m║                                                            ║\033[0m")
    print("\033[1;36m╚════════════════════════════════════════════════════════════╝\033[0m")
    print("="*70)
    
    # 功能说明区域
    print("\033[1;32m┌─ 功能说明 ───────────────────────────────────────────────┐\033[0m")
    print("\033[1;32m│\033[0m  ✓ 自动浏览 Linux.do 论坛文章                           \033[1;32m│\033[0m")
    print("\033[1;32m│\033[0m  ✓ 智能处理 Cloudflare 验证                             \033[1;32m│\033[0m")
    print("\033[1;32m│\033[0m  ✓ 自动点赞评论，提升互动                               \033[1;32m│\033[0m")
    print("\033[1;32m│\033[0m  ✓ 定时休息，模拟真实浏览行为                           \033[1;32m│\033[0m")
    print("\033[1;32m│\033[0m  ✓ 详细日志输出，实时监控运行状态                       \033[1;32m│\033[0m")
    print("\033[1;32m└─────────────────────────────────────────────────────────┘\033[0m")
    print("="*70)
    
    # 显示启动选项菜单
    print("\n\033[1;35m┌─ 启动选项 ───────────────────────────────────────────────┐\033[0m")
    print("\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m")
    print("\033[1;35m│\033[0m  \033[1;33m[1]\033[0m \033[1m正常模式\033[0m - 仅显示基本信息                      \033[1;35m│\033[0m")
    print("\033[1;35m│\033[0m  \033[1;33m[2]\033[0m \033[1m调试模式\033[0m - 显示详细日志和运行状态              \033[1;35m│\033[0m")
    print("\033[1;35m│\033[0m  \033[1;33m[3]\033[0m \033[1m退出程序\033[0m                                      \033[1;35m│\033[0m")
    print("\033[1;35m│\033[0m                                                           \033[1;35m│\033[0m")
    print("\033[1;35m└─────────────────────────────────────────────────────────┘\033[0m")
    print("="*70)
    
    # 获取用户选择
    choice = input("\n\033[1;37m请输入选择 (默认为1): \033[0m").strip()
    if choice == "3":
        print("\n\033[1;31m┌─ 程序退出 ───────────────────────────────────────────────┐\033[0m")
        print("\033[1;31m│\033[0m  感谢使用 Linux.do 自动浏览工具，再见！                  \033[1;31m│\033[0m")
        print("\033[1;31m└─────────────────────────────────────────────────────────┘\033[0m\n")
        return
    
    # 根据用户选择设置调试模式
    if choice == "2":
        CONFIG['debug'] = True
        print("\n\033[1;32m┌─ 模式选择 ───────────────────────────────────────────────┐\033[0m")
        print("\033[1;32m│\033[0m  已启用\033[1;36m调试模式\033[0m，将显示详细日志和运行状态          \033[1;32m│\033[0m")
        print("\033[1;32m└─────────────────────────────────────────────────────────┘\033[0m\n")
    else:
        CONFIG['debug'] = False
        print("\n\033[1;32m┌─ 模式选择 ───────────────────────────────────────────────┐\033[0m")
        print("\033[1;32m│\033[0m  已启用\033[1;33m正常模式\033[0m，仅显示基本信息                    \033[1;32m│\033[0m")
        print("\033[1;32m└─────────────────────────────────────────────────────────┘\033[0m\n")
    
    controller = BrowseController()
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())