# ============================================
# ربات تلگرام - بدون Flask
# ============================================

import os
import sys
import json
import random
import string
from datetime import datetime
import requests

# ===== تنظیمات =====
BOT_TOKEN = '8319089742:AAFoU3TT1hmpdiqd70fidyahUS9RG7CpVg4'
SITE_URL = 'http://dmonvpn.lol'

# ===== تابع ارسال به تلگرام =====
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

# ===== پردازش Webhook =====
def handle_webhook(update):
    try:
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '')
            first_name = msg['chat'].get('first_name', 'کاربر')
            
            if text == '/start':
                # ساخت توکن جدید
                new_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                
                # پیام به کاربر
                message = f"🎮 به ربات خوش آمدی {first_name}!\n\n"
                message += f"🔑 توکن شما: `{new_key}`\n"
                message += f"📱 این توکن رو در سایت وارد کن:\n"
                message += f"🔗 {SITE_URL}\n\n"
                message += f"⏰ ساعت الان: {datetime.now().strftime('%H:%M:%S')}"
                
                send_telegram(chat_id, message)
                print(f"✅ توکن جدید: {new_key} برای {first_name}")
                
    except Exception as e:
        print(f"Error: {e}")

# ===== ورودی اصلی =====
def main():
    # روش ۱: دریافت از طریق CGI (برای Render)
    if os.environ.get('REQUEST_METHOD') == 'POST':
        content_length = int(os.environ.get('CONTENT_LENGTH', 0))
        if content_length > 0:
            body = sys.stdin.read(content_length)
            try:
                update = json.loads(body)
                handle_webhook(update)
            except:
                pass
        print("Status: 200 OK")
        print("Content-Type: text/plain")
        print()
        print("OK")
        return
    
    # روش ۲: دریافت از طریق استاندارد (برای تست محلی)
    else:
        # نمایش HTML ساده
        print("Content-Type: text/html")
        print()
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ربات تلگرام</title>
            <style>
                * {{ margin:0; padding:0; box-sizing:border-box; }}
                body {{
                    background: #0a0a1a;
                    color: #fff;
                    font-family: 'Segoe UI', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    text-align: center;
                    padding: 20px;
                }}
                .box {{
                    background: rgba(255,255,255,0.05);
                    padding: 40px;
                    border-radius: 20px;
                    border: 1px solid rgba(255,255,255,0.05);
                    max-width: 500px;
                    width: 100%;
                }}
                h1 {{ color: #FFD700; font-size: 28px; }}
                .status {{ color: #00ff88; font-size: 18px; margin: 15px 0; }}
                .btn {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 30px;
                    background: #FFD700;
                    color: #000;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: bold;
                }}
                .site-link {{ color: rgba(255,255,255,0.15); font-size: 12px; margin-top: 20px; }}
                .site-link a {{ color: #FFD700; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🤖 ربات تلگرام</h1>
                <p class="status">✅ فعال و آنلاین</p>
                <p style="color:rgba(255,255,255,0.2);font-size:13px;">
                    🔗 آدرس: {os.environ.get('HTTP_HOST', 'localhost')}
                </p>
                <a href="/set_webhook" class="btn">⚙️ تنظیم Webhook</a>
                <div class="site-link">
                    🌐 سایت: <a href="{SITE_URL}" target="_blank">{SITE_URL}</a>
                </div>
            </div>
        </body>
        </html>
        '''
        print(html)

if __name__ == '__main__':
    main()
