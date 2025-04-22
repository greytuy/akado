# 浏览配置
CONFIG = {
    'scroll': {
        'min_speed': 10,  # 最小滚动速度(毫秒)
        'max_speed': 15,  # 最大滚动速度
        'min_distance': 2,  # 最小滚动距离
        'max_distance': 4,  # 最大滚动距离
        'check_interval': 500,  # 检查间隔
        'fast_scroll_chance': 0.08,  # 快速滚动概率
        'fast_scroll_min': 80,  # 最小快速滚动距离
        'fast_scroll_max': 200  # 最大快速滚动距离
    },
    'time': {
        'browse_time': 3600000,  # 浏览时间(毫秒)
        'rest_time': 600000,  # 休息时间
        'min_pause': 300,  # 最小暂停时间
        'max_pause': 500,  # 最大暂停时间
        'load_wait': 1500,  # 加载等待时间
    },
    'article': {
        'comment_limit': 1000,  # 评论数限制
        'topic_list_limit': 100,  # 话题列表限制
        'retry_limit': 3  # 重试次数限制
    },
    'must_read': {
        'posts': [
            {
                'id': '1051',
                'url': 'https://linux.do/t/topic/1051/'
            },
            {
                'id': '5973',
                'url': 'https://linux.do/t/topic/5973'
            },
            {
                'id': '102770',
                'url': 'https://linux.do/t/topic/102770'
            },
            {
                'id': '154010',
                'url': 'https://linux.do/t/topic/154010'
            },
            {
                'id': '149576',
                'url': 'https://linux.do/t/topic/149576'
            },
            {
                'id': '22118',
                'url': 'https://linux.do/t/topic/22118'
            },
        ],
        'likes_needed': 5  # 需要点赞的数量
    }
}