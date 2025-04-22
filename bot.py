# bot.py
import os
import time
import random
import logging
import tempfile
import re
import requests
import subprocess
import urllib.parse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from telegram import Update, InputMediaPhoto
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# -------------------- 日志配置 --------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def print_and_log(msg: str):
    """同时在控制台打印和写入 logger"""
    print(msg, flush=True)
    logger.info(msg)

# -------------------- 全局常量 --------------------
TELEGRAM_BOT_TOKEN = "TOKEN"  # 替换为你的 Bot Token

# 当返回的 HTML 长度低于该值，或包含 “Tweet not found” 时视为被反爬拦截
MIN_HTML_SIZE = 5000  

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.5735.199 Mobile Safari/537.36",
]

# -------------------- 工具函数 --------------------
def is_blocked_html(html: str) -> bool:
    """
    判断 HTML 是否被反爬拦截：
    - 长度过短（小于 MIN_HTML_SIZE）
    - 或包含 “Tweet not found”
    """
    if not html or len(html) < MIN_HTML_SIZE:
        return True
    if "Tweet not found" in html:
        return True
    return False

def random_delay(base: float = 1.0, var: float = 2.0):
    """防爬随机延时"""
    sec = base + random.uniform(0, var)
    print_and_log(f"[delay] 等待 {sec:.1f} 秒")
    time.sleep(sec)

def convert_to_nitter(url: str) -> str:
    """
    将 x.com/twitter.com 链接转换为 nitter.net 链接
    """
    for p in [r'https?://(?:www\.)?x\.com/(.+)', r'https?://(?:www\.)?twitter\.com/(.+)']:
        m = re.match(p, url)
        if m:
            return f'https://nitter.net/{m.group(1)}'
    return url

def extract_true_m3u8_url(html: str) -> str:
    """
    从 <video data-url="..."> 提取真实的 m3u8 链接
    """
    soup = BeautifulSoup(html, 'html.parser')
    tag = soup.find('video', {'data-url': True})
    if tag:
        parts = tag['data-url'].split('/', 3)
        if len(parts) == 4:
            return urllib.parse.unquote(parts[3])
    return None

def download_m3u8_with_ffmpeg(m3u8_url: str, output_file: str) -> str:
    """
    调用 ffmpeg 下载 m3u8 流并保存为 mp4
    """
    cmd = ['ffmpeg', '-y', '-i', m3u8_url, '-c', 'copy', output_file]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_file
    except Exception as e:
        print_and_log(f"[error] ffmpeg 下载失败: {e}")
        return None

# -------------------- 下载推文视频 --------------------
async def download_tweet_video(tweet_url: str) -> str:
    """
    用 Selenium 打开 Nitter 推文页，自动点击“Enable hls playback”并下载视频
    UA 会依次轮换，直到拿到有效页面或用完所有 UA
    返回本地视频文件路径，失败返回 None
    """
    nitter_url = convert_to_nitter(tweet_url)
    temp_dir = tempfile.mkdtemp()
    video_path = None
    html = None
    driver = None

    # 依次尝试不同 UA
    for ua in USER_AGENTS:
        try:
            print_and_log(f"[UA try] 下载视频，使用 UA: {ua[:40]}...")
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument(f'--user-agent={ua}')

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
            driver.get(nitter_url)
            time.sleep(5)  # 等待页面渲染

            html = driver.page_source
            if is_blocked_html(html):
                print_and_log("[warn] UA 被拦截或页面不完整，尝试下一个 UA")
                driver.quit()
                driver = None
                continue

            print_and_log("[info] 成功获取页面，开始点击播放按钮")
            # 点击 “Enable hls playback”
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Enable hls playback')]")
                btn.click()
                print_and_log("[selenium] 点击 Enable hls playback")
                time.sleep(5)
            except Exception as e:
                print_and_log(f"[warn] 点击按钮失败或按钮不存在: {e}")

            # 再次拿页面，提取 m3u8
            html = driver.page_source
            m3u8 = extract_true_m3u8_url(html)
            if m3u8:
                print_and_log(f"[info] 找到 m3u8 链接: {m3u8}")
                out = os.path.join(temp_dir, "video.mp4")
                dl = download_m3u8_with_ffmpeg(m3u8, out)
                if dl and os.path.exists(dl):
                    video_path = dl
                    print_and_log(f"[info] 视频下载完成: {dl}")
            break  # 无论有没有下载成功，都跳出 UA 循环
        except Exception as ex:
            print_and_log(f"[error] 视频 UA 轮换异常: {ex}")
            if driver:
                driver.quit()
                driver = None
            continue

    # 清理浏览器
    if driver:
        driver.quit()

    return video_path

# -------------------- 下载推文图片 --------------------
async def download_tweet_images(tweet_url: str) -> list:
    """
    加载 Nitter 推文页，**只获取主推文者**的图片并下载
    UA 会依次轮换，直到拿到有效页面或用完所有 UA
    返回本地图片路径列表
    """
    nitter_url = convert_to_nitter(tweet_url)
    temp_dir = tempfile.mkdtemp()
    paths = []
    html = None
    driver = None

    # 先 UA 轮换，获取有效页面
    for ua in USER_AGENTS:
        try:
            print_and_log(f"[UA try] 下载图片，使用 UA: {ua[:40]}...")
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument(f'--user-agent={ua}')

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
            driver.get(nitter_url)
            time.sleep(5)

            html = driver.page_source
            if is_blocked_html(html):
                print_and_log("[warn] UA 被拦截或页面不完整，尝试下一个 UA")
                driver.quit()
                driver = None
                continue

            print_and_log("[info] 成功获取页面，开始解析图片")
            break
        except Exception as e:
            print_and_log(f"[error] 图片 UA 轮换异常: {e}")
            if driver:
                driver.quit()
                driver = None
            continue

    if not html:
        print_and_log("[error] 所有 UA 均无法获取有效页面，放弃下载图片")
        return paths

    # 解析只属于主推文的图片
    soup = BeautifulSoup(html, 'html.parser')
    main_tweet = (
        soup.select_one('#m') or
        soup.select_one('.main-tweet') or
        soup.select_one('.conversation')
    )
    if main_tweet:
        media_imgs = main_tweet.select('img[src*="media"]')
        print_and_log(f"[info] 在主推文中找到 {len(media_imgs)} 张图片")
    else:
        media_imgs = soup.select('img[src*="media"]')
        print_and_log(f"[warn] 未定位到主推文，回退全局，共 {len(media_imgs)} 张图片")

    headers = {'User-Agent': ua}
    for img in media_imgs:
        src = img.get('src')
        if not src or 'profile_images' in src:
            continue
        full = src if src.startswith('http') else f'https://nitter.net{src}'
        full = full.replace('name=small', 'name=orig').replace('name=medium', 'name=orig')
        print_and_log(f"[info] 下载图片: {full}")
        try:
            resp = requests.get(full, headers=headers, timeout=15)
            if resp.status_code == 200:
                name = os.path.basename(urllib.parse.urlparse(full).path) or f"img_{int(time.time())}.jpg"
                fp = os.path.join(temp_dir, name)
                with open(fp, 'wb') as f:
                    f.write(resp.content)
                paths.append(fp)
        except Exception as e:
            print_and_log(f"[warn] 图片下载异常: {e}")

    # 清理浏览器
    if driver:
        driver.quit()

    print_and_log(f"[info] 最终下载 {len(paths)} 张图片")
    return paths

# -------------------- 下载用户头像 --------------------
async def download_user_avatar(url: str) -> str:
    """
    用 Selenium 加载 Nitter 用户主页并下载头像
    返回本地头像文件路径，失败返回 None
    """
    nitter_url = convert_to_nitter(url)
    avatar_path = None

    # 头像抓取也做 UA 轮换
    for ua in USER_AGENTS:
        driver = None
        try:
            print_and_log(f"[UA try] 下载头像，使用 UA: {ua[:40]}...")
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument(f'--user-agent={ua}')

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
            driver.get(nitter_url)
            time.sleep(5)

            html = driver.page_source
            if is_blocked_html(html):
                print_and_log("[warn] UA 被拦截或页面不完整，尝试下一个 UA")
                driver.quit()
                continue

            soup = BeautifulSoup(html, 'html.parser')
            avatar = soup.select_one('.profile-card .profile-card-avatar img') or \
                     soup.select_one('img.avatar, img.profile-card-avatar')
            if avatar:
                src = avatar.get('src')
                if src and 'default_profile' not in src:
                    full = src if src.startswith('http') else f'https://nitter.net{src}'
                    full = full.replace('name=small', 'name=orig').replace('name=medium', 'name=orig')
                    print_and_log(f"[info] 下载头像: {full}")
                    resp = requests.get(full, headers={'User-Agent': ua}, timeout=15)
                    if resp.status_code == 200:
                        name = os.path.basename(urllib.parse.urlparse(full).path) or 'avatar.jpg'
                        tmp = tempfile.mkdtemp()
                        avatar_path = os.path.join(tmp, name)
                        with open(avatar_path, 'wb') as f:
                            f.write(resp.content)
            break
        except Exception as e:
            print_and_log(f"[warn] 头像 UA 轮换异常: {e}")
            if driver:
                driver.quit()
            continue
        finally:
            if driver:
                driver.quit()

    return avatar_path

# -------------------- 处理 Telegram 消息 --------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    if 'x.com' not in text and 'twitter.com' not in text:
        return

    m = re.search(r'https?://(?:www\.)?(?:x\.com|twitter\.com)/[^\s]+', text)
    if not m:
        return
    url = m.group(0)

    # 用户主页 => 头像
    if re.match(r'https?://(?:www\.)?(?:x\.com|twitter\.com)/[^/]+/?$', url):
        try:
            avatar = await download_user_avatar(url)
            if avatar:
                with open(avatar, 'rb') as ph:
                    await update.message.reply_photo(photo=ph, reply_to_message_id=update.message.message_id)
                os.remove(avatar)
        except Exception as e:
            print_and_log(f"[warn] 发送头像失败: {e}")
        return

    # 推文页 => 优先视频
    try:
        video = await download_tweet_video(url)
        if video:
            with open(video, 'rb') as vf:
                await update.message.reply_video(video=vf, reply_to_message_id=update.message.message_id)
            os.remove(video)
            return
    except Exception as e:
        print_and_log(f"[warn] 视频下载失败，改为图片：{e}")

    # 再下载图片
    try:
        imgs = await download_tweet_images(url)
        if imgs:
            if len(imgs) == 1:
                with open(imgs[0], 'rb') as ph:
                    await update.message.reply_photo(photo=ph, reply_to_message_id=update.message.message_id)
            else:
                media = [InputMediaPhoto(open(p, 'rb')) for p in imgs]
                for i in range(0, len(media), 10):
                    await update.message.reply_media_group(
                        media=media[i:i+10],
                        reply_to_message_id=update.message.message_id
                    )
            for p in imgs:
                os.remove(p)
    except Exception as e:
        print_and_log(f"[error] 发送图片失败：{e}")

# -------------------- 错误处理 --------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"更新时发生错误: {context.error}")

# -------------------- 主程序入口 --------------------
def main():
    print_and_log("Bot 启动中...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
