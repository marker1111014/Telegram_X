# Telegram Nitter 媒体下载 Bot

一个基于 Python 的 Telegram 机器人，能够自动下载并发送来自 X.com（原 Twitter）推文中的视频、图片以及用户头像。  
该机器人通过将推文链接转换为 Nitter 页面，结合 Selenium 模拟浏览器操作、BeautifulSoup 解析页面、FFmpeg 下载视频流，实现对推特媒体内容的无障碍抓取。

## 功能特点
- 自动识别并下载推文中的视频（优先级最高）  
- 在视频下载失败时，改为下载推文中的图片  
- 支持多图群发  
- 可单独下载用户主页头像  
- 内置多 User‑Agent 轮换和延时策略，降低反爬拦截风险  

## 技术栈及依赖
- Python 3.7+
- python-telegram-bot（v20+）
- selenium
- webdriver-manager
- beautifulsoup4
- requests
- FFmpeg（用于下载和合并 m3u8 视频流）
- Google Chrome 或 Chromium 浏览器

## 快速开始

1. 克隆仓库  
   ```bash
   git clone https://github.com/your-repo/telegram-nitter-bot.git
   cd telegram-nitter-bot
   ```

2. 安装依赖  
   建议使用虚拟环境：  
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   *requirements.txt 示例：*  
   ```
   python-telegram-bot>=20.0
   selenium
   webdriver-manager
   beautifulsoup4
   requests
   ```

3. 安装系统依赖  
   - 安装 Chrome / Chromium 浏览器  
   - 安装 FFmpeg (`sudo apt-get install ffmpeg` 或对应系统包管理器)

4. 配置 Bot Token  
   在 `bot.py` 中，将 `TELEGRAM_BOT_TOKEN = "TOKEN"` 替换为你自己的 Telegram Bot Token，或通过环境变量管理：
   ```bash
   export TELEGRAM_BOT_TOKEN="你的 Bot Token"
   ```

5. 运行机器人  
   ```bash
   python bot.py
   ```

## 使用说明
- 在 Telegram 中向你的 Bot 发送任意含有 `x.com` 或 `twitter.com` 的链接  
- 如果是用户主页链接（非推文），Bot 会返回用户头像  
- 如果是推文链接，Bot 会：
  1. 尝试下载视频并发送  
  2. 若视频下载失败，改为抓取并发送图片  

## 代码结构与主要模块

- **bot.py**  
  - `convert_to_nitter(url)`：将 X/Twitter 链接转换为 Nitter 页面地址  
  - `is_blocked_html(html)`：检测页面是否被反爬拦截  
  - `extract_true_m3u8_url(html)`：从 Nitter 页面中提取真实 m3u8 视频流地址  
  - `download_m3u8_with_ffmpeg(m3u8_url, output_file)`：调用 FFmpeg 下载并保存为 MP4  
  - `download_tweet_video(tweet_url)`：完整的视频下载流程（UA 轮换、点击 HLS 播放按钮等）  
  - `download_tweet_images(tweet_url)`：下载推文中主作者的图片列表  
  - `download_user_avatar(url)`：下载用户主页头像  
  - `handle_message(update, context)`：主消息处理函数，根据链接类型分发下载任务  
  - `error_handler(update, context)`：统一捕获并记录错误  

## 注意事项
- Nitter 服务偶有不可用或 IP 限制，可能导致抓取失败  
- 确保服务器环境安装了对应版本的 Chrome/Chromium 与 FFmpeg  
- 本项目仅用于学习与研究，请勿用于商业非法用途  

## 许可协议
本项目遵循 MIT License，欢迎贡献与讨论。
