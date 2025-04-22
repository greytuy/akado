import asyncio
import random
import time
from typing import Optional, List, Dict

from playwright.async_api import async_playwright, Page, Browser
import requests

from config import CONFIG

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

    async def initialize(self):
        """初始化浏览器和页面"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()

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
        print(f'已获取 {len(topic_list)} 篇文章')

    async def get_next_topic(self):
        """获取下一个要浏览的话题"""
        if not self.topic_list:
            await self.get_latest_topics()

        if self.topic_list:
            return self.topic_list.pop(0)
        return None

    async def navigate_next_topic(self):
        """导航到下一个话题"""
        next_topic = await self.get_next_topic()
        if next_topic:
            print(f"导航到新文章: {next_topic.get('title', '未知标题')}")
            url = f"https://linux.do/t/topic/{next_topic['id']}"
            if next_topic.get('last_read_post_number'):
                url += f"/{next_topic['last_read_post_number']}"
            await self.page.goto(url)
            await asyncio.sleep(2)  # 等待页面加载
        else:
            print("没有更多文章，返回首页")
            await self.page.goto("https://linux.do/latest")

    async def like_random_comment(self) -> bool:
        """随机点赞评论"""
        if not self.auto_running:
            return False

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

        if visible_buttons:
            # 随机选择一个按钮
            random_button = random.choice(visible_buttons)
            # 滚动到按钮位置
            await random_button.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            if not self.auto_running:
                return False

            print('找到可点赞的评论，准备点赞')
            await random_button.click()
            self.likes_count += 1
            await asyncio.sleep(1)
            return True

        # 如果找不到可点赞的按钮，往下滚动
        await self.page.evaluate('window.scrollBy(0, 500)')
        await asyncio.sleep(1)

        print('当前位置没有找到可点赞的评论，继续往下找')
        return False

    async def handle_first_use(self):
        """处理首次使用的必读文章"""
        if not self.auto_running:
            return

        # 如果还没有选择文章
        if not self.selected_post:
            # 随机选择一篇必读文章
            self.selected_post = random.choice(CONFIG['must_read']['posts'])
            print(f'随机选择文章: {self.selected_post["url"]}')
            await self.page.goto(self.selected_post['url'])
            await asyncio.sleep(2)
            return

        current_url = self.page.url

        # 如果在选中的文章页面
        if self.selected_post['url'] in current_url:
            print(f'当前在选中的文章页面，已点赞数: {self.likes_count}')

            while self.likes_count < CONFIG['must_read']['likes_needed'] and self.auto_running:
                # 尝试点赞随机评论
                success = await self.like_random_comment()
                if success and self.likes_count >= CONFIG['must_read']['likes_needed']:
                    print('完成所需点赞数量，开始正常浏览')
                    self.first_use_checked = True
                    await self.get_latest_topics()
                    await self.navigate_next_topic()
                    break

                await asyncio.sleep(1)
        else:
            # 如果不在选中的文章页面，导航过去
            await self.page.goto(self.selected_post['url'])

    async def start_scrolling(self):
        """开始滚动浏览"""
        if self.is_scrolling:
            return

        self.is_scrolling = True
        self.last_action_time = time.time() * 1000

        while self.is_scrolling:
            speed = random.randint(CONFIG['scroll']['min_speed'], CONFIG['scroll']['max_speed'])
            distance = random.randint(CONFIG['scroll']['min_distance'], CONFIG['scroll']['max_distance'])
            scroll_step = distance * 2.5

            # 执行滚动
            await self.page.evaluate(f'window.scrollBy(0, {scroll_step})')

            if await self.is_near_bottom():
                await asyncio.sleep(0.8)

                if await self.is_near_bottom() and await self.is_page_loaded():
                    print("已到达页面底部，准备导航到下一篇文章...")
                    await asyncio.sleep(1)
                    await self.navigate_next_topic()
                    break

            await asyncio.sleep(speed / 1000)  # 转换为秒
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
        self.accumulated_time += now - self.last_action_time
        self.last_action_time = now

        if self.accumulated_time >= CONFIG['time']['browse_time']:
            self.accumulated_time = 0
            await self.pause_for_rest()

    async def pause_for_rest(self):
        """暂停休息"""
        self.is_scrolling = False
        print("休息10分钟...")
        await asyncio.sleep(CONFIG['time']['rest_time'] / 1000)  # 转换为秒
        print("休息结束，继续浏览...")
        await self.start_scrolling()

    def stop_scrolling(self):
        """停止滚动"""
        self.is_scrolling = False
        self.auto_running = False

    async def run(self):
        """运行浏览器自动化"""
        try:
            await self.initialize()
            self.auto_running = True

            # 首先访问首页
            await self.page.goto('https://linux.do')
            await asyncio.sleep(2)

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
        finally:
            await self.close()

async def main():
    controller = BrowseController()
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())