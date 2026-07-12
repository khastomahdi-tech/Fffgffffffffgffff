# ============================================
# ربات تلگرام - نسخه قدیمی و ساده
# برای Python 3.6 تا 3.11
# ============================================

from flask import Flask, request, jsonify
import requests
import random
import string
from datetime import datetime
import sys

app = Flask(__name__)

# ===== تنظیمات =====
BOT_TOKEN = '8319089742:AAFoU3TT1hmpdiqd70fidyahUS9RG7CpVg4'
SITE_URL = 'http://dmonvpn.lol'

# ===== تابع ارسال به تلگرام =====
def send_telegram(chat_id, text):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        return response
    except Exception as e:
        print("Error:", e)
        return None

# ===== پردازش Webhook =====
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        try:
            update = request.get_json()
            if update and 'message' in update:
                msg = update['message']
                chat_id = msg['chat']['id']
                text = msg.get('text', '')
                first_name = msg['chat'].get('first_name', 'کاربر')
                
                if text == '/start':
                    # ساخت توکن جدید
                    new_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                    
                    # ارسال به کاربر
                    message = "🎮 به ربات خوش آمدی " + first_name + "!\n\n"
                    message += "🔑 توکن شما: `" + new_key + "`\n"
                    message += "📱 این توکن رو در سایت وارد کن:\n"
                    message += "🔗 " + SITE_URL + "\n\n"
                    message += "⏰ ساعت الان: " + datetime.now().strftime('%H:%M:%S')
                    
                    send_telegram(chat_id, message)
                    print("✅ توکن جدید:", new_key, "برای", first_name)
        except Exception as e:
            print("Error:", e)
        return 'OK', 200
    
    # ===== نمایش وضعیت (برای مرورگر) =====
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ربات تلگرام</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
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
            }
            .box {
                background: rgba(255,255,255,0.05);
                padding: 40px;
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.05);
                max-width: 500px;
                width: 100%;
            }
            h1 { 
                color: #FFD700;
                font-size: 28px;
            }
            .status { color: #00ff88; font-size: 18px; margin: 15px 0; }
            .btn {
                display: inline-block;
                margin-top: 20px;
                padding: 12px 30px;
                background: #FFD700;
                color: #000;
                border-radius: 12px;
                text-decoration: none;
                font-weight: bold;
                transition: 0.3s;
            }
            .btn:hover { transform: scale(1.05); }
            .site-link {
                color: rgba(255,255,255,0.15);
                font-size: 12px;
                margin-top: 20px;
            }
            .site-link a { color: #FFD700; text-decoration: none; }
            .url {
                color: rgba(255,255,255,0.3);
                font-size: 13px;
                margin-top: 15px;
                word-break: break-all;
                background: rgba(255,255,255,0.03);
                padding: 10px;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🤖 ربات تلگرام</h1>
            <p class="status">✅ فعال و آنلاین</p>
            <div class="url">
                🔗 آدرس: ''' + request.url_root + '''
            </div>
            <a href="/set_webhook" class="btn">⚙️ تنظیم Webhook</a>
            <div class="site-link">
                🌐 سایت: <a href="''' + SITE_URL + '''" target="_blank">''' + SITE_URL + '''</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# ===== تنظیم Webhook =====
@app.route('/set_webhook')
def set_webhook():
    webhook_url = request.url_root
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/setWebhook?url=" + webhook_url
    try:
        response = requests.get(url, timeout=10)
        return "<pre>" + response.text + "</pre>"
    except Exception as e:
        return "<pre>❌ خطا: " + str(e) + "</pre>"

# ===== اجرا =====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
