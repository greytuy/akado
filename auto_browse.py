from playwright.sync_api import sync_playwright
import random
import time
import os

class AutoBrowser:
    def __init__(self):
        self.config = {
            'scroll': {
                'min_speed': 10,
                'max_speed': 15,
                'min_distance': 2,
                'max_distance': 4,
                'fast_scroll_chance': 0.08,
                'fast_scroll_min': 80,
                'fast_scroll_max': 200
            },
            'time': {
                'browse_time': 3600,  # 1小时
                'rest_time': 600,     # 10分钟
                'min_pause': 0.3,
                'max_pause': 0.5,
            }
        }
        
    def random_sleep(self, min_time, max_time):
        time.sleep(random.uniform(min_time, max_time))
        
    def run(self):
        with sync_playwright() as p:
            # 使用无头浏览器，添加反检测
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # 登录处理
            page.goto('https://linux.do/login')
            page.fill('input[name="login-account"]', os.environ['LINUX_DO_USERNAME'])
            page.fill('input[name="login-password"]', os.environ['LINUX_DO_PASSWORD'])
            page.click('button[type="submit"]')
            
            # 等待登录完成
            page.wait_for_load_state('networkidle')
            
            # 获取文章列表
            page.goto('https://linux.do/latest')
            page.wait_for_selector('.topic-list tr')
            
            # 获取所有文章链接
            topics = page.query_selector_all('.topic-list tr td.main-link a')
            topic_urls = [topic.get_attribute('href') for topic in topics]
            
            # 浏览文章
            for url in topic_urls[:10]:  # 限制浏览数量
                page.goto(f'https://linux.do{url}')
                page.wait_for_load_state('networkidle')
                
                # 模拟滚动
                last_height = page.evaluate('document.documentElement.scrollHeight')
                while True:
                    # 随机滚动
                    scroll_step = random.randint(
                        self.config['scroll']['min_distance'],
                        self.config['scroll']['max_distance']
                    ) * 100
                    
                    page.evaluate(f'window.scrollBy(0, {scroll_step})')
                    self.random_sleep(
                        self.config['time']['min_pause'],
                        self.config['time']['max_pause']
                    )
                    
                    # 随机快速滚动
                    if random.random() < self.config['scroll']['fast_scroll_chance']:
                        fast_scroll = random.randint(
                            self.config['scroll']['fast_scroll_min'],
                            self.config['scroll']['fast_scroll_max']
                        )
                        page.evaluate(f'window.scrollBy(0, {fast_scroll})')
                        self.random_sleep(0.2, 0.3)
                    
                    new_height = page.evaluate('document.documentElement.scrollHeight')
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                # 文章间休息
                self.random_sleep(2, 4)
            
            browser.close()

if __name__ == '__main__':
    browser = AutoBrowser()
    browser.run()