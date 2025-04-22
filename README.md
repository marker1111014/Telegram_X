# Telegram Nitter 媒體下載 Bot

壹個基於 Python 的 Telegram 機器人，能夠自動下載並發送來自 X.com（原 Twitter）推文中的視頻、圖片以及用戶頭像。  
該機器人通過將推文鏈接轉換為 Nitter 頁面，結合 Selenium 模擬瀏覽器操作、BeautifulSoup 解析頁面、FFmpeg 下載視頻流，實現對推特媒體內容的無障礙抓取。

## 功能特點
- 自動識別並下載推文中的視頻（優先級最高）  
- 在視頻下載失敗時，改為下載推文中的圖片  
- 支持多圖群發  
- 可單獨下載用戶主頁頭像  
- 內置多 User‑Agent 輪換和延時策略，降低反爬攔截風險  

## 技術棧及依賴
- Python 3.7+
- python-telegram-bot（v20+）
- selenium
- webdriver-manager
- beautifulsoup4
- requests
- FFmpeg（用於下載和合並 m3u8 視頻流）
- Google Chrome 或 Chromium 瀏覽器

## 快速開始

1. 克隆倉庫  
   ```bash
   git clone https://github.com/your-repo/telegram-nitter-bot.git
   cd telegram-nitter-bot
   ```

2. 安裝依賴  
   建議使用虛擬環境：  
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

3. 安裝系統依賴  
   - 安裝 Chrome / Chromium 瀏覽器  
   - 安裝 FFmpeg (`sudo apt-get install ffmpeg` 或對應系統包管理器)

4. 配置 Bot Token  
   在 `bot.py` 中，將 `TELEGRAM_BOT_TOKEN = "TOKEN"` 替換為妳自己的 Telegram Bot Token，或通過環境變量管理：
   ```bash
   export TELEGRAM_BOT_TOKEN="妳的 Bot Token"
   ```

5. 運行機器人  
   ```bash
   python bot.py
   ```

## 使用說明
- 在 Telegram 中向妳的 Bot 發送任意含有 `x.com` 或 `twitter.com` 的鏈接  
- 如果是用戶主頁鏈接（非推文），Bot 會返回用戶頭像  
- 如果是推文鏈接，Bot 會：
  1. 嘗試下載視頻並發送  
  2. 若視頻下載失敗，改為抓取並發送圖片  

## 代碼結構與主要模塊

- **bot.py**  
  - `convert_to_nitter(url)`：將 X/Twitter 鏈接轉換為 Nitter 頁面地址  
  - `is_blocked_html(html)`：檢測頁面是否被反爬攔截  
  - `extract_true_m3u8_url(html)`：從 Nitter 頁面中提取真實 m3u8 視頻流地址  
  - `download_m3u8_with_ffmpeg(m3u8_url, output_file)`：調用 FFmpeg 下載並保存為 MP4  
  - `download_tweet_video(tweet_url)`：完整的視頻下載流程（UA 輪換、點擊 HLS 播放按鈕等）  
  - `download_tweet_images(tweet_url)`：下載推文中主作者的圖片列表  
  - `download_user_avatar(url)`：下載用戶主頁頭像  
  - `handle_message(update, context)`：主消息處理函數，根據鏈接類型分發下載任務  
  - `error_handler(update, context)`：統壹捕獲並記錄錯誤  

## 註意事項
- Nitter 服務偶有不可用或 IP 限制，可能導致抓取失敗  
- 確保服務器環境安裝了對應版本的 Chrome/Chromium 與 FFmpeg  
- 本項目僅用於學習與研究，請勿用於商業非法用途  

## 許可協議
本項目遵循 MIT License，歡迎貢獻與討論。
