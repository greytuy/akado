// ==UserScript==
// @name        自动浏览linux.do,autoBrowse-linux.do
// @description 自动浏览linux.do的帖子和话题，智能滚动和加载检测
// @namespace   http://tampermonkey.net/
// @match       https://linux.do/*
// @grant       none
// @version     1.2.4
// @author      quantumcat
// @license     MIT
// @icon        https://www.google.com/s2/favicons?domain=linux.do

// ==/UserScript==

// 配置项
const CONFIG = {
    scroll: {
      minSpeed: 10,
      maxSpeed: 15,
      minDistance: 2,
      maxDistance: 4,
      checkInterval: 500,
      fastScrollChance: 0.08,
      fastScrollMin: 80,
      fastScrollMax: 200
    },
    time: {
      browseTime: 3600000,
      restTime: 600000,
      minPause: 300,
      maxPause: 500,
      loadWait: 1500,
    },
    article: {
      commentLimit: 1000,
      topicListLimit: 100,
      retryLimit: 3
    },
  
    mustRead: {
      posts: [
        {
          id: '1051',
          url: 'https://linux.do/t/topic/1051/'
        },
        {
          id: '5973',
          url: 'https://linux.do/t/topic/5973'
        },
        // 在这里添加更多文章
        {
          id: '102770',
          url: 'https://linux.do/t/topic/102770'
        },
        // 示例格式
        {
          id: '154010',
          url: 'https://linux.do/t/topic/154010'
        },
        {
          id: '149576',
          url: 'https://linux.do/t/topic/149576'
        },
        {
          id: '22118',
          url: 'https://linux.do/t/topic/22118'
        },
      ],
      likesNeeded: 5  // 需要点赞的数量
    },
  
    // 设置界面的默认配置
    ui: {
      position: 'right', // 'left' 或 'right'
      collapsed: false
    }
  };
  
  // 工具函数
  const Utils = {
    random: (min, max) => Math.floor(Math.random() * (max - min + 1)) + min,
  
    sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms)),
  
    isPageLoaded: () => {
      const loadingElements = document.querySelectorAll('.loading, .infinite-scroll');
      return loadingElements.length === 0;
    },
  
    isNearBottom: () => {
      const { scrollHeight, clientHeight, scrollTop } = document.documentElement;
      return (scrollTop + clientHeight) >= (scrollHeight - 200);
    },
  
    debounce: (func, wait) => {
      let timeout;
      return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    }
  };
  
  // 存储管理
  const Storage = {
    get: (key, defaultValue = null) => {
      try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : defaultValue;
      } catch {
        return defaultValue;
      }
    },
  
    set: (key, value) => {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        console.error('Storage error:', error);
        return false;
      }
    }
  };
  
  
  class BrowseController {
    constructor() {
      this.isScrolling = false;
      this.scrollInterval = null;
      this.pauseTimeout = null;
      this.accumulatedTime = Storage.get('accumulatedTime', 0);
      this.lastActionTime = Date.now();
      this.isTopicPage = window.location.href.includes("/t/topic/");
      this.autoRunning = Storage.get('autoRunning', false);
      this.topicList = Storage.get('topicList', []);
      this.firstUseChecked = Storage.get('firstUseChecked', false);
      this.likesCount = Storage.get('likesCount', 0);
      this.selectedPost = Storage.get('selectedPost', null);
  
      // 从存储加载UI设置
      this.uiSettings = Storage.get('uiSettings', CONFIG.ui);
  
      this.setupSidebar();
  
      // 如果是第一次使用,先处理必读文章
      if (!this.firstUseChecked) {
        this.handleFirstUse();
      } else if (this.autoRunning) {
        if (this.isTopicPage) {
          this.startScrolling();
        } else {
          this.getLatestTopics().then(() => this.navigateNextTopic());
        }
      }
    }
  
    setupSidebar() {
      // 创建侧边栏容器
      this.sidebar = document.createElement("div");
      Object.assign(this.sidebar.style, {
        position: "fixed",
        [this.uiSettings.position]: "0",
        top: "20%",
        padding: "10px",
        backgroundColor: "white",
        color: "black",
        borderRadius: this.uiSettings.position === 'left' ? "0 5px 5px 0" : "5px 0 0 5px",
        boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
        zIndex: "9999",
        transition: "transform 0.3s ease",
        transform: this.uiSettings.collapsed ?
          (this.uiSettings.position === 'left' ? "translateX(-90%)" : "translateX(90%)") :
          "translateX(0)",
        cursor: "move" // 指示可拖动
      });
  
      // 添加拖拽功能
      this.addDragFunctionality();
  
      // 创建标题
      const title = document.createElement("h3");
      title.textContent = "Linux.do 阅读助手";
      title.style.margin = "0 0 10px 0";
      title.style.textAlign = "center";
      title.style.cursor = "pointer";
      this.sidebar.appendChild(title);
  
      // 创建主按钮
      this.button = document.createElement("button");
      Object.assign(this.button.style, {
        width: "100%",
        padding: "10px",
        marginBottom: "10px",
        fontSize: "16px",
        backgroundColor: this.autoRunning ? "#f44336" : "#4CAF50",
        border: "none",
        borderRadius: "5px",
        color: "white",
        cursor: "pointer"
      });
      this.button.textContent = this.autoRunning ? "停止" : "开始阅读";
      this.button.addEventListener("click", () => this.handleButtonClick());
      this.sidebar.appendChild(this.button);
  
      // 添加展开/折叠按钮
      const toggleButton = document.createElement("button");
      toggleButton.textContent = "≡";
      Object.assign(toggleButton.style, {
        position: "absolute",
        [this.uiSettings.position === 'left' ? 'right' : 'left']: "-25px",
        top: "10px",
        width: "25px",
        height: "25px",
        padding: "0",
        fontSize: "16px",
        backgroundColor: "#eee",
        border: "none",
        borderRadius: this.uiSettings.position === 'left' ? "0 5px 5px 0" : "5px 0 0 5px",
        cursor: "pointer"
      });
      toggleButton.addEventListener("click", () => this.toggleSidebar());
      this.sidebar.appendChild(toggleButton);
  
      // 添加设置区域
      this.setupSettingsPanel();
  
      // 将侧边栏添加到页面
      document.body.appendChild(this.sidebar);
    }
  
    // 添加拖拽功能
    addDragFunctionality() {
      let isDragging = false;
      let offsetX = 0;
      let offsetY = 0;
      let startPosition = null;
  
      // 鼠标按下开始拖拽
      this.sidebar.addEventListener('mousedown', (e) => {
        // 如果点击的是按钮元素，不触发拖拽
        if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') {
          return;
        }
  
        isDragging = true;
        startPosition = this.uiSettings.position; // 记录开始的位置
        offsetX = e.clientX;
        offsetY = e.clientY;
  
        // 防止文本选中
        e.preventDefault();
      });
  
      // 鼠标移动时拖拽
      document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
  
        const dx = e.clientX - offsetX;
        const dy = e.clientY - offsetY;
  
        // 更新位置
        this.sidebar.style.left = startPosition === 'left' ? `${dx}px` : 'auto';
        this.sidebar.style.right = startPosition === 'right' ? `${-dx}px` : 'auto';
        this.sidebar.style.top = `calc(20% + ${dy}px)`;
      });
  
      // 鼠标松开结束拖拽
      document.addEventListener('mouseup', () => {
        isDragging = false;
      });
    }
  
    toggleSidebar() {
      this.uiSettings.collapsed = !this.uiSettings.collapsed;
      Storage.set('uiSettings', this.uiSettings);
      this.sidebar.style.transform = this.uiSettings.collapsed ?
        (this.uiSettings.position === 'left' ? "translateX(-90%)" : "translateX(90%)") :
        "translateX(0)";
    }
  
    setupSettingsPanel() {
      // 创建设置按钮
      const settingsButton = document.createElement("button");
      settingsButton.textContent = "设置";
      Object.assign(settingsButton.style, {
        width: "100%",
        padding: "8px",
        marginBottom: "10px",
        backgroundColor: "#007bff",
        border: "none",
        borderRadius: "5px",
        color: "white",
        cursor: "pointer"
      });
  
      // 创建设置面板容器
      const settingsPanel = document.createElement("div");
      settingsPanel.style.display = "none";
      settingsPanel.style.marginTop = "10px";
  
      // 添加位置设置
      const positionDiv = document.createElement("div");
      positionDiv.style.marginBottom = "10px";
  
      const positionLabel = document.createElement("label");
      positionLabel.textContent = "位置: ";
      positionDiv.appendChild(positionLabel);
  
      const positionSelect = document.createElement("select");
      positionSelect.style.width = "100%";
  
      const leftOption = document.createElement("option");
      leftOption.value = "left";
      leftOption.textContent = "左侧";
      leftOption.selected = this.uiSettings.position === 'left';
  
      const rightOption = document.createElement("option");
      rightOption.value = "right";
      rightOption.textContent = "右侧";
      rightOption.selected = this.uiSettings.position === 'right';
  
      positionSelect.appendChild(leftOption);
      positionSelect.appendChild(rightOption);
      positionDiv.appendChild(positionSelect);
  
      // 添加点赞数量设置
      const likesNeededDiv = document.createElement("div");
      likesNeededDiv.style.marginBottom = "10px";
  
      const likesNeededLabel = document.createElement("label");
      likesNeededLabel.textContent = "需要点赞的数量: ";
      likesNeededLabel.style.display = "block";
      likesNeededDiv.appendChild(likesNeededLabel);
  
      const likesNeededInput = document.createElement("input");
      likesNeededInput.type = "number";
      likesNeededInput.min = "1";
      likesNeededInput.max = "50";
      likesNeededInput.value = CONFIG.mustRead.likesNeeded;
      likesNeededInput.style.width = "100%";
      likesNeededDiv.appendChild(likesNeededInput);
  
      // 添加保存按钮
      const saveButton = document.createElement("button");
      saveButton.textContent = "保存设置";
      Object.assign(saveButton.style, {
        width: "100%",
        padding: "8px",
        marginTop: "10px",
        backgroundColor: "#28a745",
        border: "none",
        borderRadius: "5px",
        color: "white",
        cursor: "pointer"
      });
  
      saveButton.addEventListener("click", () => {
        const newPosition = positionSelect.value;
        const newLikesNeeded = parseInt(likesNeededInput.value) || 5;
  
        // 更新设置并保存
        this.uiSettings.position = newPosition;
        Storage.set('uiSettings', this.uiSettings);
  
        // 更新点赞设置
        CONFIG.mustRead.likesNeeded = newLikesNeeded;
        Storage.set('likesNeeded', newLikesNeeded);
  
        // 应用新设置
        this.applySidebarSettings();
  
        // 关闭设置面板
        settingsPanel.style.display = "none";
      });
  
      // 组合设置面板
      settingsPanel.appendChild(positionDiv);
      settingsPanel.appendChild(likesNeededDiv);
      settingsPanel.appendChild(saveButton);
  
      // 设置按钮点击事件
      settingsButton.addEventListener("click", () => {
        if (settingsPanel.style.display === "none") {
          settingsPanel.style.display = "block";
        } else {
          settingsPanel.style.display = "none";
        }
      });
  
      // 添加到侧边栏
      this.sidebar.appendChild(settingsButton);
      this.sidebar.appendChild(settingsPanel);
    }
  
    applySidebarSettings() {
      // 应用位置设置
      this.sidebar.style.left = this.uiSettings.position === 'left' ? "0" : "auto";
      this.sidebar.style.right = this.uiSettings.position === 'right' ? "0" : "auto";
      this.sidebar.style.borderRadius = this.uiSettings.position === 'left' ? "0 5px 5px 0" : "5px 0 0 5px";
  
      // 重置折叠状态
      this.sidebar.style.transform = this.uiSettings.collapsed ?
        (this.uiSettings.position === 'left' ? "translateX(-90%)" : "translateX(90%)") :
        "translateX(0)";
    }
  
    async handleFirstUse() {
      if (!this.autoRunning) return; // 如果没有运行，直接返回
  
      // 如果还没有选择文章
      if (!this.selectedPost) {
        // 随机选择一篇必读文章
        const randomIndex = Math.floor(Math.random() * CONFIG.mustRead.posts.length);
        this.selectedPost = CONFIG.mustRead.posts[randomIndex];
        Storage.set('selectedPost', this.selectedPost);
        console.log(`随机选择文章: ${this.selectedPost.url}`);
  
        // 导航到选中的文章
        window.location.href = this.selectedPost.url;
        return;
      }
  
      const currentUrl = window.location.href;
  
      // 如果在选中的文章页面
      if (currentUrl.includes(this.selectedPost.url)) {
        console.log(`当前在选中的文章页面，已点赞数: ${this.likesCount}`);
  
        while (this.likesCount < CONFIG.mustRead.likesNeeded && this.autoRunning) {
          // 尝试点赞随机评论
          await this.likeRandomComment();
  
          if (this.likesCount >= CONFIG.mustRead.likesNeeded) {
            console.log('完成所需点赞数量，开始正常浏览');
            Storage.set('firstUseChecked', true);
            this.firstUseChecked = true;
            await this.getLatestTopics();
            await this.navigateNextTopic();
            break;
          }
  
          await Utils.sleep(1000); // 点赞间隔
        }
      } else {
        // 如果不在选中的文章页面，导航过去
        window.location.href = this.selectedPost.url;
      }
    }
  
    handleButtonClick() {
      if (this.isScrolling || this.autoRunning) {
        // 停止所有操作
        this.stopScrolling();
        this.autoRunning = false;
        Storage.set('autoRunning', false);
        this.button.textContent = "开始阅读";
        this.button.style.backgroundColor = "#4CAF50";
      } else {
        // 开始运行
        this.autoRunning = true;
        Storage.set('autoRunning', true);
        this.button.textContent = "停止";
        this.button.style.backgroundColor = "#f44336";
  
        if (!this.firstUseChecked) {
          // 开始处理必读文章
          this.handleFirstUse();
        } else if (this.isTopicPage) {
          this.startScrolling();
        } else {
          this.getLatestTopics().then(() => this.navigateNextTopic());
        }
      }
    }
  
    async likeRandomComment() {
      if (!this.autoRunning) return false; // 如果停止运行，立即返回
  
      // 获取所有评论的点赞按钮
      const likeButtons = Array.from(document.querySelectorAll('.like-button, .like-count, [data-like-button], .discourse-reactions-reaction-button'))
        .filter(button =>
          button &&
          button.offsetParent !== null &&
          !button.classList.contains('has-like') &&
          !button.classList.contains('liked')
        );
  
      if (likeButtons.length > 0) {
        // 随机选择一个未点赞的按钮
        const randomButton = likeButtons[Math.floor(Math.random() * likeButtons.length)];
        // 滚动到按钮位置
        randomButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await Utils.sleep(1000);
  
        if (!this.autoRunning) return false; // 再次检查是否停止运行
  
        console.log('找到可点赞的评论，准备点赞');
        randomButton.click();
        this.likesCount++;
        Storage.set('likesCount', this.likesCount);
        await Utils.sleep(1000);
        return true;
      }
  
      // 如果找不到可点赞的按钮，往下滚动一段距离
      window.scrollBy({
        top: 500,
        behavior: 'smooth'
      });
      await Utils.sleep(1000);
  
      console.log('当前位置没有找到可点赞的评论，继续往下找');
      return false;
    }
  
    async getLatestTopics() {
      let page = 1;
      let topicList = [];
      let retryCount = 0;
  
      while (topicList.length < CONFIG.article.topicListLimit && retryCount < CONFIG.article.retryLimit) {
        try {
          const response = await fetch(`https://linux.do/latest.json?no_definitions=true&page=${page}`);
          const data = await response.json();
  
          if (data?.topic_list?.topics) {
            const filteredTopics = data.topic_list.topics.filter(topic =>
              topic.posts_count < CONFIG.article.commentLimit
            );
            topicList.push(...filteredTopics);
            page++;
          } else {
            break;
          }
        } catch (error) {
          console.error('获取文章列表失败:', error);
          retryCount++;
          await Utils.sleep(1000);
        }
      }
  
      if (topicList.length > CONFIG.article.topicListLimit) {
        topicList = topicList.slice(0, CONFIG.article.topicListLimit);
      }
  
      this.topicList = topicList;
      Storage.set('topicList', topicList);
      console.log(`已获取 ${topicList.length} 篇文章`);
    }
  
    async getNextTopic() {
      if (this.topicList.length === 0) {
        await this.getLatestTopics();
      }
  
      if (this.topicList.length > 0) {
        const topic = this.topicList.shift();
        Storage.set('topicList', this.topicList);
        return topic;
      }
  
      return null;
    }
  
    async startScrolling() {
      if (this.isScrolling) return;
  
      this.isScrolling = true;
      this.button.textContent = "停止";
      this.button.style.backgroundColor = "#f44336";
      this.lastActionTime = Date.now();
  
      while (this.isScrolling) {
        const speed = Utils.random(CONFIG.scroll.minSpeed, CONFIG.scroll.maxSpeed);
        const distance = Utils.random(CONFIG.scroll.minDistance, CONFIG.scroll.maxDistance);
        const scrollStep = distance * 2.5;
  
        window.scrollBy({
          top: scrollStep,
          behavior: 'smooth'
        });
  
        if (Utils.isNearBottom()) {
          await Utils.sleep(800);
  
          if (Utils.isNearBottom() && Utils.isPageLoaded()) {
            console.log("已到达页面底部，准备导航到下一篇文章...");
            await Utils.sleep(1000);
            await this.navigateNextTopic();
            break;
          }
        }
  
        await Utils.sleep(speed);
        this.accumulateTime();
  
        if (Math.random() < CONFIG.scroll.fastScrollChance) {
          const fastScroll = Utils.random(CONFIG.scroll.fastScrollMin, CONFIG.scroll.fastScrollMax);
          window.scrollBy({
            top: fastScroll,
            behavior: 'smooth'
          });
          await Utils.sleep(200);
        }
      }
    }
  
    async waitForPageLoad() {
      let attempts = 0;
      const maxAttempts = 5;
  
      while (attempts < maxAttempts) {
        if (Utils.isPageLoaded()) {
          return true;
        }
        await Utils.sleep(300);
        attempts++;
      }
  
      return false;
    }
  
    stopScrolling() {
      this.isScrolling = false;
      clearInterval(this.scrollInterval);
      clearTimeout(this.pauseTimeout);
      this.button.textContent = "开始阅读";
      this.button.style.backgroundColor = "#4CAF50";
    }
  
    accumulateTime() {
      const now = Date.now();
      this.accumulatedTime += now - this.lastActionTime;
      Storage.set('accumulatedTime', this.accumulatedTime);
      this.lastActionTime = now;
  
      if (this.accumulatedTime >= CONFIG.time.browseTime) {
        this.accumulatedTime = 0;
        Storage.set('accumulatedTime', 0);
        this.pauseForRest();
      }
    }
  
    async pauseForRest() {
      this.stopScrolling();
      console.log("休息10分钟...");
      await Utils.sleep(CONFIG.time.restTime);
      console.log("休息结束，继续浏览...");
      this.startScrolling();
    }
  
    async navigateNextTopic() {
      const nextTopic = await this.getNextTopic();
      if (nextTopic) {
        console.log("导航到新文章:", nextTopic.title);
        const url = nextTopic.last_read_post_number
          ? `https://linux.do/t/topic/${nextTopic.id}/${nextTopic.last_read_post_number}`
          : `https://linux.do/t/topic/${nextTopic.id}`;
        window.location.href = url;
      } else {
        console.log("没有更多文章，返回首页");
        window.location.href = "https://linux.do/latest";
      }
    }
  
    // 添加重置方法（可选，用于测试）
    resetFirstUse() {
      Storage.set('firstUseChecked', false);
      Storage.set('likesCount', 0);
      Storage.set('selectedPost', null);
      this.firstUseChecked = false;
      this.likesCount = 0;
      this.selectedPost = null;
      console.log('已重置首次使用状态');
    }
  }
  
  // 初始化
  (function () {
    new BrowseController();
  })();