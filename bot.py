# bot.py - کد کامل با پشتیبانی از کاستوم ایموجی در همه بخش‌ها
import telebot
import sqlite3
import re
import random
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
from telebot.types import MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
import time
import os
import json
import requests
import threading
import subprocess

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = "8319089742:AAFoU3TT1hmpdiqd70fidyahUS9RG7CpVg4"
OWNER_ID = 7323216202
BOT_USERNAME = "@DEMONFREECONF_BOT"
PING_THRESHOLD = 130
PING_INTERVAL = 60

DEFAULT_WELCOME_EMOJI_ID = "5900199258316869673"

bot = telebot.TeleBot(BOT_TOKEN)
context = {}
edit_page_data = {}
EDIT_PAGE_SIZE = 10

# ==================== دیتابیس ====================
def init_db():
    db = sqlite3.connect("bot.db", check_same_thread=False)
    cursor = db.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in columns:
            print("🔄 ساختار دیتابیس قدیمی است، در حال بازسازی...")
            cursor.execute("DROP TABLE users")
            table_exists = None
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        name TEXT PRIMARY KEY,
        text TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        config TEXT,
        ip TEXT,
        port TEXT,
        protocol TEXT,
        used_by TEXT,
        expiry TEXT,
        ping INTEGER DEFAULT 0,
        last_ping_check TEXT,
        last_ping_notification TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY,
        daily_count INTEGER DEFAULT 0,
        last_reset TEXT,
        servers TEXT DEFAULT '[]',
        first_name TEXT,
        username TEXT,
        joined_at TEXT,
        last_emoji_msg_id TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ping_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT,
        user_id TEXT,
        ping INTEGER,
        reported_at TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT,
        user_id TEXT,
        report_text TEXT,
        reported_at TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    db.commit()
    return db, cursor

db, cursor = init_db()

# ==================== توابع دیتابیس ====================

def get_all_users():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, daily_count, servers, first_name, username, joined_at FROM users")
        return c.fetchall()
    finally:
        conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        if not data:
            return {"daily_count": 0, "last_reset": datetime.now().isoformat(), "servers": [], "first_name": "", "username": "", "joined_at": datetime.now().isoformat(), "last_emoji_msg_id": None}
        
        try:
            last_reset = datetime.fromisoformat(data[2]).date()
        except:
            last_reset = datetime.now().date()
        
        today = datetime.now().date()
        if last_reset != today:
            conn2 = sqlite3.connect("bot.db", check_same_thread=False)
            c2 = conn2.cursor()
            try:
                c2.execute("UPDATE users SET daily_count=0, last_reset=? WHERE user_id=?",
                           (datetime.now().isoformat(), str(user_id)))
                conn2.commit()
            finally:
                conn2.close()
            return {"daily_count": 0, "last_reset": datetime.now().isoformat(), "servers": json.loads(data[3]) if data[3] else [], "first_name": data[4], "username": data[5], "joined_at": data[6], "last_emoji_msg_id": data[7] if len(data) > 7 else None}
        
        return {
            "daily_count": data[1],
            "last_reset": data[2],
            "servers": json.loads(data[3]) if data[3] else [],
            "first_name": data[4] if len(data) > 4 else "",
            "username": data[5] if len(data) > 5 else "",
            "joined_at": data[6] if len(data) > 6 else datetime.now().isoformat(),
            "last_emoji_msg_id": data[7] if len(data) > 7 else None
        }
    finally:
        conn.close()

def update_user_data(user_id, daily_count=None, servers=None, last_emoji_msg_id=None):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        if daily_count is not None:
            c.execute("UPDATE users SET daily_count=? WHERE user_id=?", (daily_count, str(user_id)))
        if servers is not None:
            c.execute("UPDATE users SET servers=? WHERE user_id=?", (json.dumps(servers), str(user_id)))
        if last_emoji_msg_id is not None:
            c.execute("UPDATE users SET last_emoji_msg_id=? WHERE user_id=?", (last_emoji_msg_id, str(user_id)))
        conn.commit()
    finally:
        conn.close()

def update_user_info(user_id, first_name, username):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (first_name, username, str(user_id)))
        conn.commit()
    finally:
        conn.close()

def get_user_servers(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT servers FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        if data and data[0]:
            try:
                return json.loads(data[0])
            except:
                return eval(data[0])
        return []
    finally:
        conn.close()

def save_user_servers(user_id, servers_list):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO users(user_id, servers) VALUES(?,?)", (str(user_id), json.dumps(servers_list)))
        conn.commit()
    finally:
        conn.close()

def save_message(name, text):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO messages(name,text) VALUES(?,?)", (name, text))
        conn.commit()
    finally:
        conn.close()

def get_message(name):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT text FROM messages WHERE name=?", (name,))
        data = c.fetchone()
        return data[0] if data else None
    finally:
        conn.close()

def get_all_messages():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT name, text FROM messages")
        return c.fetchall()
    finally:
        conn.close()

def add_server(config, ip="Unknown", port="Unknown", protocol="vless"):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO servers(config, ip, port, protocol, used_by, expiry, ping, last_ping_check, last_ping_notification) VALUES(?,?,?,?,?,?,?,?,?)",
                  (config, ip, port, protocol, None, None, 0, None, None))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def get_free_servers():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM servers WHERE used_by IS NULL")
        return c.fetchall()
    finally:
        conn.close()

def get_server_by_id(server_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM servers WHERE id=?", (server_id,))
        return c.fetchone()
    finally:
        conn.close()

def assign_server_to_user(server_id, user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET used_by=?, expiry=? WHERE id=?", (str(user_id), None, server_id))
        conn.commit()
    finally:
        conn.close()

def remove_server(server_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM servers WHERE id=?", (server_id,))
        conn.commit()
    finally:
        conn.close()

def update_server_ping(server_id, ping):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET ping=?, last_ping_check=? WHERE id=?", (ping, datetime.now().isoformat(), server_id))
        conn.commit()
    finally:
        conn.close()

def update_server_ping_notification(server_id, last_notification):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET last_ping_notification=? WHERE id=?", (last_notification, server_id))
        conn.commit()
    finally:
        conn.close()

def get_server_ping_notification(server_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT last_ping_notification FROM servers WHERE id=?", (server_id,))
        data = c.fetchone()
        return data[0] if data and data[0] else None
    finally:
        conn.close()

def update_server_config(server_id, new_config):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET config=? WHERE id=?", (new_config, server_id))
        conn.commit()
    finally:
        conn.close()

def get_total_servers():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers")
        return c.fetchone()[0]
    finally:
        conn.close()

def get_free_servers_count():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers WHERE used_by IS NULL")
        return c.fetchone()[0]
    finally:
        conn.close()

def get_used_servers_count():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers WHERE used_by IS NOT NULL")
        return c.fetchone()[0]
    finally:
        conn.close()

def save_ping_report(server_id, user_id, ping):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO ping_reports(server_id, user_id, ping, reported_at) VALUES(?,?,?,?)",
                  (server_id, str(user_id), ping, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_pending_ping_reports():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM ping_reports WHERE status='pending'")
        return c.fetchall()
    finally:
        conn.close()

def update_ping_report_status(report_id, status):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE ping_reports SET status=? WHERE id=?", (status, report_id))
        conn.commit()
    finally:
        conn.close()

def save_server_report(server_id, user_id, report_text):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO server_reports(server_id, user_id, report_text, reported_at) VALUES(?,?,?,?)",
                  (server_id, str(user_id), report_text, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_pending_server_reports():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM server_reports WHERE status='pending'")
        return c.fetchall()
    finally:
        conn.close()

def update_server_report_status(report_id, status):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE server_reports SET status=? WHERE id=?", (status, report_id))
        conn.commit()
    finally:
        conn.close()

def set_bot_setting(key, value):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO bot_settings(key, value) VALUES(?,?)", (key, value))
        conn.commit()
    finally:
        conn.close()

def get_bot_setting(key):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
        data = c.fetchone()
        return data[0] if data else None
    finally:
        conn.close()

def get_required_channels():
    channels = get_bot_setting("required_channels")
    if channels:
        try:
            return json.loads(channels)
        except:
            return eval(channels)
    return []

def set_required_channels(channels_list):
    set_bot_setting("required_channels", json.dumps(channels_list))

def check_user_in_channel(user_id, channel_username):
    try:
        member = bot.get_chat_member(f"@{channel_username}", user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

def check_all_channels(user_id):
    channels = get_required_channels()
    if not channels:
        return True, []
    
    not_member = []
    for channel in channels:
        if not check_user_in_channel(user_id, channel):
            not_member.append(channel)
    
    return len(not_member) == 0, not_member

# ==================== توابع کمکی ====================

def utf16_len(text):
    return len(text.encode("utf-16-le")) // 2

def parse_custom_emoji(text):
    if not text:
        return "", []
    
    pattern = r"\[emoji:(\d+)\]"
    entities = []
    clean_text = ""
    last_index = 0
    
    for match in re.finditer(pattern, text):
        before = text[last_index:match.start()]
        clean_text += before
        emoji_offset = utf16_len(clean_text)
        clean_text += "⭐"
        entities.append(
            MessageEntity(
                type="custom_emoji",
                offset=emoji_offset,
                length=utf16_len("⭐"),
                custom_emoji_id=match.group(1)
            )
        )
        last_index = match.end()
    
    clean_text += text[last_index:]
    return clean_text, entities

def format_message_with_vars(text, vars_dict):
    if not text:
        return text
    
    for key, value in vars_dict.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
        text = text.replace(f"{{{key}}}", str(value))
    
    return text

def get_welcome_emoji():
    emoji = get_bot_setting("welcome_emoji")
    if not emoji:
        emoji = DEFAULT_WELCOME_EMOJI_ID
    return emoji

def set_welcome_emoji(emoji_id):
    set_bot_setting("welcome_emoji", emoji_id)

def send_separate_emoji(chat_id, emoji_id):
    try:
        user_data = get_user_data(chat_id)
        last_emoji_msg_id = user_data.get("last_emoji_msg_id")
        
        if last_emoji_msg_id:
            try:
                bot.delete_message(chat_id, int(last_emoji_msg_id))
            except:
                pass
        
        sent_msg = bot.send_message(
            chat_id,
            "⭐",
            entities=[MessageEntity(
                type="custom_emoji",
                offset=0,
                length=1,
                custom_emoji_id=emoji_id
            )]
        )
        
        update_user_data(chat_id, last_emoji_msg_id=str(sent_msg.message_id))
        return True
    except Exception as e:
        print(f"Error sending separate emoji: {e}")
        return False

def send_custom_message(chat_id, text, reply_markup=None, parse_mode="HTML", vars_dict=None, send_emoji_first=True):
    if not text:
        return None
    
    if send_emoji_first:
        emoji_id = get_welcome_emoji()
        send_separate_emoji(chat_id, emoji_id)
    
    if vars_dict:
        text = format_message_with_vars(text, vars_dict)
    
    try:
        message_text, entities = parse_custom_emoji(text)
        return bot.send_message(
            chat_id,
            message_text,
            entities=entities if entities else None,
            reply_markup=reply_markup,
            parse_mode=parse_mode if not entities else None
        )
    except Exception as e:
        print(f"Error sending message: {e}")
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def edit_custom_message(message, text, reply_markup=None, vars_dict=None):
    if not text:
        return None
    
    if vars_dict:
        text = format_message_with_vars(text, vars_dict)
    
    try:
        message_text, entities = parse_custom_emoji(text)
        return bot.edit_message_text(
            message_text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            entities=entities if entities else None,
            reply_markup=reply_markup,
            parse_mode=None
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        try:
            return bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=reply_markup)
        except:
            return None

def generate_qr(config_text):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(config_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

def get_server_name(user_id):
    return f"{user_id}_{BOT_USERNAME}_1GB"

def create_hashtag(user_id, username):
    now = datetime.now()
    return f"#{user_id}_{username}_{now.strftime('%Y%m%d')}_نامحدود_1GB"

def add_hashtag_to_config(config, user_id, username):
    hashtag = create_hashtag(user_id, username)
    return f"{config}{hashtag}"

def get_location_from_ip(ip):
    if ip == "Unknown" or not ip:
        return "نامشخص"
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return f"{data.get('city', '')}, {data.get('country', '')}"
        return "نامشخص"
    except:
        return "نامشخص"

def ping_server(config):
    try:
        ip_match = re.search(r'@([^:]+)', config)
        if ip_match:
            ip = ip_match.group(1)
            result = subprocess.run(['ping', '-c', '1', '-W', '2', ip], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                time_match = re.search(r'time=(\d+\.?\d*)\s*ms', result.stdout)
                if time_match:
                    return int(float(time_match.group(1)))
        return 0
    except Exception as e:
        print(f"Error pinging server: {e}")
        return 0

def check_all_servers_ping():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT id, config, used_by FROM servers WHERE used_by IS NOT NULL")
        servers = c.fetchall()
    finally:
        conn.close()
    
    for server_id, config, user_id in servers:
        ping = ping_server(config)
        update_server_ping(server_id, ping)
        
        if ping > PING_THRESHOLD and ping > 0:
            last_notification = get_server_ping_notification(server_id)
            
            if not last_notification:
                should_notify = True
            else:
                try:
                    last_time = datetime.fromisoformat(last_notification)
                    diff = (datetime.now() - last_time).total_seconds()
                    should_notify = diff > 300
                except:
                    should_notify = True
            
            if should_notify:
                save_ping_report(server_id, user_id, ping)
                update_server_ping_notification(server_id, datetime.now().isoformat())
                
                msg = f"""⚠️ **هشدار پینگ بالا!**

🆔 سرور: {server_id}
👤 کاربر: {user_id}
📊 پینگ: {ping} ms
⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}

لطفاً برای آپدیت سرویس اقدام کنید."""
                
                bot.send_message(OWNER_ID, msg, parse_mode="Markdown")

def start_ping_scheduler():
    def ping_loop():
        while True:
            try:
                print("🔄 در حال بررسی پینگ سرورها...")
                check_all_servers_ping()
                print("✅ بررسی پینگ کامل شد")
            except Exception as e:
                print(f"❌ خطا در بررسی پینگ: {e}")
            time.sleep(PING_INTERVAL)
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    print(f"🚀 تایمر بررسی پینگ راه‌اندازی شد (هر {PING_INTERVAL} ثانیه)")

# ==================== کیبوردها ====================

def get_main_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📥 دریافت سرور", callback_data="get_free_server"),
        InlineKeyboardButton("📋 سرویس‌های من", callback_data="my_services")
    )
    keyboard.add(
        InlineKeyboardButton("👤 حساب کاربری", callback_data="my_account"),
        InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
    )
    
    if int(user_id) == OWNER_ID:
        keyboard.add(
            InlineKeyboardButton("🔧 پنل مدیریت", callback_data="admin_panel")
        )
    return keyboard

def get_server_action_keyboard(server_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 QR Code", callback_data=f"qr_{server_id}"),
        InlineKeyboardButton("📋 مشخصات", callback_data=f"info_{server_id}")
    )
    keyboard.add(
        InlineKeyboardButton("📄 کانفیگ", callback_data=f"config_{server_id}"),
        InlineKeyboardButton("📊 پینگ", callback_data=f"ping_{server_id}")
    )
    keyboard.add(
        InlineKeyboardButton("⚠️ گزارش خرابی", callback_data=f"report_{server_id}"),
        InlineKeyboardButton("🗑 حذف سرویس", callback_data=f"delete_{server_id}")
    )
    keyboard.add(
        InlineKeyboardButton("✏️ تغییر نام", callback_data=f"rename_{server_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_services")
    )
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("➕ اضافه کردن", callback_data="admin_add_servers")
    )
    keyboard.add(
        InlineKeyboardButton("🗑 حذف سرور", callback_data="admin_remove_server"),
        InlineKeyboardButton("📋 کاربران", callback_data="admin_users")
    )
    keyboard.add(
        InlineKeyboardButton("✏️ ویرایش پیام‌ها", callback_data="admin_edit_messages"),
        InlineKeyboardButton("📊 پینگ بالا", callback_data="admin_ping_reports")
    )
    keyboard.add(
        InlineKeyboardButton("⚠️ گزارش خرابی", callback_data="admin_server_reports"),
        InlineKeyboardButton("🔄 آپدیت سرویس", callback_data="admin_update_service")
    )
    keyboard.add(
        InlineKeyboardButton("📢 چنل‌های اجباری", callback_data="admin_required_channels"),
        InlineKeyboardButton("📨 ارسال همگانی", callback_data="admin_broadcast")
    )
    keyboard.add(
        InlineKeyboardButton("🗑 حذف دیتابیس", callback_data="admin_delete_db"),
        InlineKeyboardButton("✏️ تنظیم ایموجی", callback_data="admin_set_emoji")
    )
    keyboard.add(
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
    )
    return keyboard

def get_back_keyboard(callback):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data=callback))
    return keyboard

# ==================== پیام‌های پیش‌فرض ====================

DEFAULT_MESSAGES = {
    "welcome": """
[emoji:5900199258316869673] **سلام {first_name} عزیز!**

[emoji:5780806262774042817] به ربات مدیریت سرورهای رایگان خوش آمدید!

[emoji:5902172654055460877] **با این ربات می‌تونید:**
✅ هر روز ۲ تا سرور رایگان V2Ray بگیرید
✅ سرورهای خودتون رو مدیریت کنید
✅ QR Code و مشخصات سرورها رو ببینید
✅ حساب کاربری خودتون رو مشاهده کنید

[emoji:5900199258316869673] **قوانین:**
• هر کاربر روزانه ۲ سرور دریافت میکنه
• حجم هر سرور: ۱ گیگابایت
• مدت زمان: نامحدود

[emoji:5780806262774042817] لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
""",
    
    "help": """
[emoji:5900199258316869673] **راهنما و قوانین:**

[emoji:5780806262774042817] **۱. دریافت سرور رایگان:**
- هر کاربر روزانه ۲ سرور دریافت میکنه
- حجم هر سرور: ۱ گیگابایت
- مدت زمان: نامحدود

[emoji:5902172654055460877] **۲. سرویس‌های من:**
- مشاهده لیست سرورهای دریافت شده
- دریافت QR Code
- مشاهده مشخصات سرور
- دریافت کانفیگ (کپی با یک کلیک)
- مشاهده پینگ سرور
- گزارش خرابی سرویس
- حذف سرویس
- تغییر نام سرور

[emoji:5900199258316869673] **۳. حساب کاربری:**
- مشاهده آیدی عددی
- مشاهده نام و یوزرنیم
- تعداد سرورهای فعال

[emoji:5780806262774042817] **۴. نکات مهم:**
- سرورها کاملاً رایگان هستن
- مدت زمان سرورها نامحدوده

[emoji:5902172654055460877] در صورت مشکل با پشتیبانی تماس بگیرید.
""",
    
    "server_building": """
[emoji:5900199258316869673] ⏳ **سرور رایگان شما در حال ساخته شدن هست...**
لطفاً چند لحظه صبر کنید.
""",
    
    "server_created": """
[emoji:5780806262774042817] ✅ **سرویس شما با موفقیت ایجاد شد!**

📌 **نام سرور:** {server_name}

[emoji:5902172654055460877] می‌تونید از بخش **سرویس‌های من**، سرویس خود رو مشاهده کنید.
""",
    
    "no_free_servers": """
[emoji:5900199258316869673] ❌ **مشکل در ارتباط با پنل!**

متأسفانه در حال حاضر هیچ سرور آزادی موجود نیست.
لطفاً بعداً دوباره تلاش کنید.
""",
    
    "daily_limit": """
[emoji:5780806262774042817] ⚠️ **شما امروز ۲ سرور رایگان دریافت کردید!**

هر روز فقط ۲ سرور می‌تونید دریافت کنید.
از فردا دوباره تلاش کنید.
""",
    
    "no_services": """
[emoji:5902172654055460877] 📭 **شما هیچ سرویسی دریافت نکردید!**

از بخش **"دریافت سرور"** اقدام کنید.
""",
    
    "server_info": """
[emoji:5900199258316869673] 📋 **مشخصات سرور**

🔹 **نام کانفیگ:** {name}
🔹 **پروتکل:** {protocol}
🔹 **IP:** {ip}
🔹 **پورت:** {port}
🔹 **لوکیشن:** {location}
🔹 **حجم:** {volume}
🔹 **مدت زمان:** نامحدود
🔹 **زمان دریافت:** {received}
🔹 **وضعیت:** {status}
""",
    
    "rename_prompt": """
[emoji:5780806262774042817] ✏️ **لطفاً نام جدید سرور رو وارد کنید:**

(برای انصراف /cancel رو بفرستید)
""",
    
    "rename_confirmed": """
[emoji:5902172654055460877] ✅ **نام سرور با موفقیت به '{new_name}' تغییر کرد!**

📌 می‌تونید کانفیگ جدید رو از بخش دریافت کانفیگ بگیرید.
""",
    
    "my_account": """
[emoji:5900199258316869673] 👤 **حساب کاربری شما**

🆔 **آیدی عددی:** `{user_id}`
📛 **نام:** {first_name}
👤 **یوزرنیم:** {username}
📊 **تعداد سرورهای فعال:** {active_servers}
📋 **کل سرورهای دریافت شده:** {total_servers}
⏰ **تاریخ عضویت:** {joined_at}
📈 **سرورهای امروز:** {today_count}/2

[emoji:5780806262774042817] برای مشاهده سرورها به بخش سرویس‌های من برید.
""",
    
    "ping_result": """
[emoji:5902172654055460877] 📊 **پینگ سرور {server_name}**

🔄 **وضعیت:** {status}
📶 **پینگ:** {ping} ms

{status_emoji} **توضیح:**
{description}

اگر پینگ بالاست می‌تونید از دکمه **گزارش خرابی** استفاده کنید.
""",
    
    "report_prompt": """
[emoji:5900199258316869673] ⚠️ **گزارش خرابی سرویس**

لطفاً مشکل خود را توضیح دهید:

**مثال:**
- سرور وصل نمیشه
- سرعت بسیار پایین است
- قطع و وصل مکرر

(برای انصراف /cancel رو بفرستید)
""",
    
    "report_sent": """
[emoji:5780806262774042817] ✅ **گزارش شما با موفقیت ارسال شد!**

📌 **سرور:** {server_name}
📝 **گزارش:** {report_text}

مدیریت در اسرع وقت بررسی خواهد کرد.
""",
    
    "delete_confirmation": """
[emoji:5902172654055460877] ⚠️ **آیا از حذف سرویس '{server_name}' مطمئن هستید؟**

پس از حذف، این سرویس قابل بازیابی نیست.
""",
    
    "delete_success": """
[emoji:5900199258316869673] ✅ **سرویس '{server_name}' با موفقیت حذف شد!**
""",
    
    "qr_code_sent": """
[emoji:5780806262774042817] 📱 **QR Code سرور {server_name}**

QR Code سرویس شما در زیر ارسال شده است:
""",
    
    "config_sent": """
[emoji:5902172654055460877] 📄 **کانفیگ سرور {server_name}**

🔗 **لوکیشن:** {location}

💡 **برای کپی کردن، روی متن کانفیگ کلیک کنید:**

<code>{config}</code>
""",
    
    "server_updated_notification": """
[emoji:5900199258316869673] 🔄 **سرویس شما آپدیت شده!**

📌 **نام سرور:** {server_name}

🔗 **لطفاً برای دریافت لینک جدید به بخش سرویس‌های من بروید.**

از بخش سرویس‌های من می‌تونید کانفیگ جدید رو دریافت کنید.
""",
    
    "required_channels_check": """
[emoji:5900199258316869673] **عضویت در چنل اجباری**

[emoji:5780806262774042817] برای استفاده از ربات باید عضو چنل‌های زیر باشید:

{channels}

[emoji:5902172654055460877] پس از عضویت روی دکمه **"تأیید عضویت"** کلیک کنید.
""",
    
    "required_channels_ok": """
[emoji:5900199258316869673] **✅ عضویت شما تأیید شد!**

[emoji:5780806262774042817] به ربات خوش آمدید.
می‌تونید از تمام قابلیت‌های ربات استفاده کنید.

[emoji:5902172654055460877] لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
""",
    
    "required_channels_fail": """
[emoji:5900199258316869673] **❌ شما عضو همه چنل‌های اجباری نیستید!**

[emoji:5780806262774042817] لطفاً ابتدا عضو شوید سپس روی **"تأیید عضویت"** کلیک کنید.

{channels}

[emoji:5902172654055460877] پس از عضویت روی دکمه تأیید کلیک کنید.
""",
    
    "admin_panel": """
🔧 **پنل مدیریت**

لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
""",
    
    "admin_stats": """
📊 **آمار کلی:**

🔹 **تعداد کل سرورها:** {total}
🔹 **سرورهای آزاد:** {free}
🔹 **سرورهای در حال استفاده:** {used}
🔹 **تعداد کل کاربران:** {users}

📌 **جزئیات سرورها:**
{details}
""",
    
    "admin_add_prompt": """
📝 **لطفاً کانفیگ‌های سرور رو به صورت عمده وارد کنید:**

⚠️ **هر کانفیگ در یک خط جداگانه**

**مثال:**
<code>vless://example@server1.com:443?...</code>
<code>vless://example@server2.com:443?...</code>

برای لغو /cancel رو بفرستید
""",
    
    "admin_add_success": """
✅ **{count} سرور با موفقیت به مخزن اضافه شد!**

📊 **تعداد کل سرورها:** {total}
🆔 **محدوده آی‌دی:** {id_range}

💡 برای مشاهده سرورها به بخش آمار برید.
""",
    
    "admin_users_list": """
📋 **لیست کاربران:**

{users}
""",
    
    "admin_remove_prompt": """
🗑 **لطفاً سروری که می‌خواید حذف کنید رو انتخاب کنید:**
""",
    
    "admin_remove_success": """
✅ **سرور با آی‌دی {id} با موفقیت حذف شد!**
""",
    
    "admin_edit_messages": """
✏️ **ویرایش پیام‌ها**

لطفاً بخش مورد نظر رو انتخاب کنید:

**📌 بخش‌های قابل ویرایش (فقط بخش‌های کاربران):**
• Welcome - خوش‌آمدگویی
• Help - راهنما
• Server Building - در حال ساخت
• Server Created - ساخته شد
• No Free Servers - بدون سرور
• Daily Limit - محدودیت روزانه
• No Services - بدون سرویس
• Server Info - مشخصات سرور
• Rename Prompt - تغییر نام
• Rename Confirmed - تایید تغییر
• My Account - حساب کاربری
• Ping Result - نتیجه پینگ
• Report Prompt - گزارش خرابی
• Report Sent - ارسال گزارش
• Delete Confirmation - تأیید حذف
• Delete Success - حذف موفق
• QR Code Sent - ارسال QR
• Config Sent - ارسال کانفیگ
• Server Updated Notification - آپدیت
• Required Channels Check - چک
• Required Channels OK - تایید
• Required Channels Fail - خطا

**متغیرهای قابل استفاده:**
`{{user_id}}` - آیدی عددی کاربر
`{{username}}` - یوزرنیم کاربر
`{{first_name}}` - نام کاربر
`{{server_name}}` - نام سرور
`{{server_id}}` - آی‌دی سرور
`{{config}}` - کانفیگ سرور
`{{ping}}` - میزان پینگ
`{{volume}}` - حجم سرور
`{{duration}}` - مدت زمان
`{{status}}` - وضعیت
`{{received}}` - زمان دریافت
`{{expiry}}` - زمان انقضا
`{{time}}` - زمان فعلی
`{{location}}` - لوکیشن سرور
`{{ip}}` - IP سرور
`{{port}}` - پورت سرور
`{{protocol}}` - پروتکل
`{{new_name}}` - نام جدید

برای استفاده از Custom Emoji از این فرمت استفاده کنید:
`[emoji:کد_ایموجی]`

برای لغو /cancel رو بفرستید
""",
    
    "admin_edit_prompt": """
✏️ **لطفاً متن جدید رو ارسال کنید:**

**متغیرهای قابل استفاده:**
`{{user_id}}` - آیدی عددی کاربر
`{{username}}` - یوزرنیم کاربر
`{{first_name}}` - نام کاربر
`{{server_name}}` - نام سرور
`{{server_id}}` - آی‌دی سرور
`{{config}}` - کانفیگ سرور
`{{ping}}` - میزان پینگ
`{{volume}}` - حجم سرور
`{{duration}}` - مدت زمان
`{{status}}` - وضعیت
`{{received}}` - زمان دریافت
`{{expiry}}` - زمان انقضا
`{{time}}` - زمان فعلی
`{{location}}` - لوکیشن سرور
`{{ip}}` - IP سرور
`{{port}}` - پورت سرور
`{{protocol}}` - پروتکل
`{{new_name}}` - نام جدید

برای استفاده از Custom Emoji از این فرمت استفاده کنید:
`[emoji:کد_ایموجی]`

برای لغو /cancel رو بفرستید
""",
    
    "admin_edit_success": """
✅ **پیام با موفقیت ذخیره شد!**
""",
    
    "ping_reports_list": """
📊 **گزارش‌های پینگ بالا:**

{reports}
""",
    
    "update_service_prompt": """
🔄 **آپدیت سرویس**

لطفاً آی‌دی سرور و کانفیگ جدید رو به فرمت زیر ارسال کنید:

`سرور_آی‌دی|کانفیگ_جدید`

**مثال:**
`5|vless://example@new-server.com:443?...`

برای لغو /cancel رو بفرستید
""",
    
    "required_channels_prompt": """
📢 **تنظیم چنل‌های اجباری**

لطفاً یوزرنیم چنل‌های مورد نظر رو وارد کنید:

**نکات:**
- هر چنل در یک خط جداگانه
- بدون @ وارد کنید
- ربات باید ادمین چنل باشد
- حداکثر ۱۰ چنل

**مثال:**
`my_channel1`
`my_channel2`

برای لغو /cancel رو بفرستید
""",
    
    "required_channels_set": """
✅ **چنل‌های اجباری با موفقیت تنظیم شدند!**

📢 **چنل‌های فعلی:**
{channels}

از این پس کاربران برای استفاده از ربات باید عضو این چنل‌ها باشند.
""",
    
    "required_channels_list": """
📢 **لیست چنل‌های اجباری فعلی:**

{channels}

📊 **تعداد:** {count} چنل

برای حذف یک چنل، روی دکمه مربوطه کلیک کنید.
""",
    
    "required_channel_removed": """
✅ **چنل @{channel} با موفقیت حذف شد!**

لیست چنل‌های اجباری به‌روزرسانی شد.
""",
    
    "server_reports_list": """
⚠️ **گزارش‌های خرابی سرویس:**

{reports}
""",
    
    "server_report_resolved": """
✅ **گزارش با موفقیت بررسی شد!**

🆔 سرور: {server_id}
👤 کاربر: {user_id}

وضعیت: بررسی شده
""",
    
    "admin_report_notification": """
⚠️ **گزارش خرابی سرویس جدید!**

🆔 سرور: {server_id}
👤 کاربر: {user_id}
📝 گزارش: {report_text}
⏰ زمان: {time}

لطفاً بررسی کنید.
""",
    
    "admin_set_emoji_prompt": """
✏️ **تنظیم کاستوم ایموجی**

لطفاً کد ایموجی جدید رو وارد کنید:

**مثال:**
`5900199258316869673`

برای لغو /cancel رو بفرستید
""",
    
    "admin_set_emoji_success": """
✅ **کاستوم ایموجی با موفقیت تغییر کرد!**

🆔 **کد جدید:** {emoji_id}

از این پس این ایموجی به صورت جداگانه برای کاربران ارسال خواهد شد.
""",
    
    "admin_delete_db_confirm": """
⚠️ **هشدار! حذف دیتابیس**

آیا از حذف کامل دیتابیس مطمئن هستید؟

**این کار باعث می‌شود:**
• همه کاربران حذف شوند
• همه سرورها حذف شوند
• همه پیام‌ها حذف شوند
• ربات به حالت اولیه بازگردد

این عمل **غیرقابل بازگشت** است!
""",
    
    "admin_delete_db_success": """
✅ **دیتابیس با موفقیت حذف شد!**

ربات به حالت اولیه بازگشت.
لطفاً ربات را مجدداً راه‌اندازی کنید.
""",
    
    "admin_broadcast_success": """
✅ **پیام همگانی با موفقیت ارسال شد!**

👥 **تعداد دریافت‌کنندگان:** {count} نفر
📝 **متن:** {text}
""",
    
    "admin_broadcast_prompt": """
📨 **ارسال پیام همگانی**

لطفاً پیام خود را ارسال کنید:

**نکات:**
- پیام به همه کاربران فعال ارسال خواهد شد
- می‌توانید از کاستوم ایموجی استفاده کنید
- می‌توانید یک پیام از چنل را فوروارد کنید

برای لغو /cancel رو بفرستید
"""
}

# ==================== لیست نام‌های بخش‌های کاربران ====================

USER_MESSAGE_NAMES = [
    "welcome", "help", "server_building", "server_created", 
    "no_free_servers", "daily_limit", "no_services", "server_info",
    "rename_prompt", "rename_confirmed", "my_account", "ping_result",
    "report_prompt", "report_sent", "delete_confirmation", "delete_success",
    "qr_code_sent", "config_sent", "server_updated_notification",
    "required_channels_check", "required_channels_ok", "required_channels_fail"
]

# ==================== دستور /admin ====================

@bot.message_handler(commands=["admin"])
def admin_command(message):
    if message.from_user.id == OWNER_ID:
        msg = get_message("admin_panel") or DEFAULT_MESSAGES["admin_panel"]
        send_custom_message(message.chat.id, msg, get_admin_keyboard(), send_emoji_first=False)
    else:
        bot.reply_to(message, "❌ شما دسترسی به این بخش ندارید!")

# ==================== دستور /start ====================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    update_user_info(user_id, first_name, username)
    
    channels = get_required_channels()
    if channels and int(user_id) != OWNER_ID:
        is_member, not_member = check_all_channels(user_id)
        if not is_member:
            channels_text = "\n".join([f"• @{ch}" for ch in not_member])
            msg = get_message("required_channels_check") or DEFAULT_MESSAGES["required_channels_check"]
            msg = msg.format(channels=channels_text)
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership"),
                InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")
            )
            
            send_custom_message(
                message.chat.id,
                msg,
                keyboard,
                parse_mode="HTML",
                send_emoji_first=False
            )
            return
    
    emoji_id = get_welcome_emoji()
    send_separate_emoji(message.chat.id, emoji_id)
    
    welcome_text = get_message("welcome") or DEFAULT_MESSAGES["welcome"]
    welcome_text = welcome_text.format(first_name=first_name)
    
    send_custom_message(
        message.chat.id,
        welcome_text,
        get_main_keyboard(user_id),
        send_emoji_first=False
    )

# ==================== تابع اصلی handle_callback ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    if int(user_id) != OWNER_ID:
        channels = get_required_channels()
        if channels:
            is_member, not_member = check_all_channels(user_id)
            if not is_member and data not in ["check_membership", "back_to_main"]:
                channels_text = "\n".join([f"• @{ch}" for ch in not_member])
                msg = get_message("required_channels_check") or DEFAULT_MESSAGES["required_channels_check"]
                msg = msg.format(channels=channels_text)
                
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership"),
                    InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")
                )
                
                edit_custom_message(call.message, msg, keyboard)
                bot.answer_callback_query(call.id)
                return
    
    if data == "check_membership":
        channels = get_required_channels()
        if not channels:
            bot.answer_callback_query(call.id, "✅ هیچ چنل اجباری تنظیم نشده!", show_alert=True)
            return
        
        is_member, not_member = check_all_channels(user_id)
        if is_member:
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            
            msg = get_message("required_channels_ok") or DEFAULT_MESSAGES["required_channels_ok"]
            keyboard = get_main_keyboard(user_id)
            edit_custom_message(call.message, msg, keyboard)
            bot.answer_callback_query(call.id, "✅ عضویت شما تأیید شد!", show_alert=True)
        else:
            channels_text = "\n".join([f"• @{ch}" for ch in not_member])
            msg = get_message("required_channels_fail") or DEFAULT_MESSAGES["required_channels_fail"]
            msg = msg.format(channels=channels_text)
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership"),
                InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")
            )
            
            edit_custom_message(call.message, msg, keyboard)
            bot.answer_callback_query(call.id, "❌ شما عضو همه چنل‌ها نیستید!", show_alert=True)
        return
    
    if data == "back_to_main":
        user_data = get_user_data(user_id)
        first_name = user_data.get("first_name", "")
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        
        welcome_text = get_message("welcome") or DEFAULT_MESSAGES["welcome"]
        welcome_text = welcome_text.format(first_name=first_name)
        
        edit_custom_message(call.message, welcome_text, get_main_keyboard(user_id))
        bot.answer_callback_query(call.id)
        return
    
    if data == "get_free_server":
        user_data = get_user_data(user_id)
        
        if user_data["daily_count"] >= 2:
            msg = get_message("daily_limit") or DEFAULT_MESSAGES["daily_limit"]
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
            bot.answer_callback_query(call.id)
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🟣 V2Ray", callback_data="vpn_v2ray"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, "🔍 لطفاً نوع سرور مورد نظر خود رو انتخاب کنید:", keyboard)
        bot.answer_callback_query(call.id)
        return
    
    # ادامه کد handle_callback مانند قبل...
    # (به دلیل محدودیت طول، بقیه کد در ادامه ارسال میشه)
    if data == "vpn_v2ray":
        free_servers = get_free_servers()
        
        if not free_servers:
            msg = get_message("no_free_servers") or DEFAULT_MESSAGES["no_free_servers"]
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
            bot.answer_callback_query(call.id)
            return
        
        selected = random.choice(free_servers)
        server_id = selected[0]
        config = selected[1]
        
        username = call.from_user.username or f"user{user_id}"
        config_with_hashtag = add_hashtag_to_config(config, user_id, username)
        
        assign_server_to_user(server_id, user_id)
        
        server_name = get_server_name(user_id)
        
        user_servers = get_user_servers(user_id)
        user_servers.append({
            "server_id": server_id,
            "name": server_name,
            "config": config_with_hashtag,
            "ip": selected[2],
            "port": selected[3],
            "protocol": selected[4],
            "received_at": datetime.now().isoformat(),
            "expiry": None,
            "volume": "1GB",
            "duration": "نامحدود"
        })
        save_user_servers(user_id, user_servers)
        
        user_data = get_user_data(user_id)
        update_user_data(user_id, user_data["daily_count"] + 1)
        
        building_msg = get_message("server_building") or DEFAULT_MESSAGES["server_building"]
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        msg = edit_custom_message(call.message, building_msg)
        
        time.sleep(5)
        
        created_msg = get_message("server_created") or DEFAULT_MESSAGES["server_created"]
        created_msg = created_msg.format(server_name=server_name)
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📋 سرویس‌های من", callback_data="my_services"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
        )
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_custom_message(call.message.chat.id, created_msg, keyboard, send_emoji_first=False)
        bot.answer_callback_query(call.id)
        return
    
    if data == "my_services":
        user_servers = get_user_servers(user_id)
        
        if not user_servers:
            msg = get_message("no_services") or DEFAULT_MESSAGES["no_services"]
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
            bot.answer_callback_query(call.id)
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for server in user_servers:
            keyboard.add(
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            )
        keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, "📋 لیست سرویس‌های شما:", keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("view_server_"):
        server_id = int(data.split("_")[2])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            edit_custom_message(call.message, "❌ سرور مورد نظر یافت نشد!", get_back_keyboard("back_to_main"))
            bot.answer_callback_query(call.id)
            return
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        status = "✅ فعال"
        if ping > PING_THRESHOLD and ping > 0:
            status = f"⚠️ پینگ بالا ({ping}ms)"
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(
            call.message,
            f"📌 سرور: {server['name']}\n⏳ وضعیت: {status}\n📊 حجم: {server['volume']}",
            get_server_action_keyboard(server_id)
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "back_to_services":
        user_servers = get_user_servers(user_id)
        keyboard = InlineKeyboardMarkup(row_width=1)
        for server in user_servers:
            keyboard.add(
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            )
        keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, "📋 لیست سرویس‌های شما:", keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("qr_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        try:
            qr_image = generate_qr(server["config"])
            
            msg = get_message("qr_code_sent") or DEFAULT_MESSAGES["qr_code_sent"]
            msg = msg.format(server_name=server['name'])
            
            emoji_id = get_welcome_emoji()
            send_separate_emoji(call.message.chat.id, emoji_id)
            
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
            
            bot.send_photo(
                call.message.chat.id,
                qr_image,
                caption=f"📱 QR Code سرور {server['name']}",
                reply_markup=get_back_keyboard(f"view_server_{server_id}")
            )
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ خطا در تولید QR Code!", show_alert=True)
        return
    
    if data.startswith("info_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        try:
            received = datetime.fromisoformat(server["received_at"])
        except:
            received = datetime.now()
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        status = "✅ فعال"
        if ping > PING_THRESHOLD and ping > 0:
            status = f"⚠️ پینگ بالا ({ping}ms)"
        
        ip = server['ip']
        location = get_location_from_ip(ip)
        
        msg = get_message("server_info") or DEFAULT_MESSAGES["server_info"]
        msg = msg.format(
            name=server['name'],
            protocol=server['protocol'],
            ip=ip,
            port=server['port'],
            location=location,
            volume=server['volume'],
            received=received.strftime('%Y-%m-%d %H:%M'),
            status=status
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, get_back_keyboard(f"view_server_{server_id}"))
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("config_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        ip = server['ip']
        location = get_location_from_ip(ip)
        
        msg = get_message("config_sent") or DEFAULT_MESSAGES["config_sent"]
        msg = msg.format(
            server_name=server['name'],
            location=location,
            config=server['config']
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        
        bot.send_message(
            call.message.chat.id,
            msg,
            parse_mode="HTML",
            reply_markup=get_back_keyboard(f"view_server_{server_id}")
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("ping_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        if ping == 0:
            status = "❌ نامشخص"
            status_emoji = "❓"
            description = "پینگ قابل اندازه‌گیری نیست"
        elif ping < 50:
            status = "✅ عالی"
            status_emoji = "🌟"
            description = "پینگ بسیار خوب - اتصال پایدار"
        elif ping < 100:
            status = "✅ خوب"
            status_emoji = "👍"
            description = "پینگ مناسب - اتصال قابل قبول"
        elif ping < PING_THRESHOLD:
            status = "⚠️ متوسط"
            status_emoji = "⚠️"
            description = "پینگ نسبتاً بالا - ممکنه کمی کند باشه"
        else:
            status = "❌ ضعیف"
            status_emoji = "🚫"
            description = "پینگ بسیار بالا - نیاز به بررسی دارد"
        
        msg = get_message("ping_result") or DEFAULT_MESSAGES["ping_result"]
        msg = msg.format(
            server_name=server['name'],
            status=status,
            ping=ping,
            status_emoji=status_emoji,
            description=description
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, get_back_keyboard(f"view_server_{server_id}"))
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("report_"):
        server_id = int(data.split("_")[1])
        context["report_server_id"] = server_id
        
        msg = get_message("report_prompt") or DEFAULT_MESSAGES["report_prompt"]
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard(f"view_server_{server_id}")
        )
        bot.register_next_step_handler(call.message, process_server_report, server_id, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("delete_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        msg = get_message("delete_confirmation") or DEFAULT_MESSAGES["delete_confirmation"]
        msg = msg.format(server_name=server['name'])
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_delete_{server_id}"),
            InlineKeyboardButton("❌ انصراف", callback_data=f"view_server_{server_id}")
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("confirm_delete_"):
        server_id = int(data.split("_")[2])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور یافت نشد!", show_alert=True)
            return
        
        user_servers = [s for s in user_servers if s["server_id"] != server_id]
        save_user_servers(user_id, user_servers)
        
        cursor.execute("UPDATE servers SET used_by=NULL, expiry=NULL WHERE id=?", (server_id,))
        db.commit()
        
        msg = get_message("delete_success") or DEFAULT_MESSAGES["delete_success"]
        msg = msg.format(server_name=server['name'])
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, get_back_keyboard("my_services"))
        bot.answer_callback_query(call.id, "✅ سرویس با موفقیت حذف شد!", show_alert=True)
        return
    
    if data.startswith("rename_"):
        server_id = int(data.split("_")[1])
        context["rename_server_id"] = server_id
        
        msg = get_message("rename_prompt") or DEFAULT_MESSAGES["rename_prompt"]
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard(f"view_server_{server_id}")
        )
        bot.register_next_step_handler(call.message, process_rename, server_id, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "my_account":
        user_data = get_user_data(user_id)
        
        cursor.execute("SELECT first_name, username, joined_at FROM users WHERE user_id=?", (str(user_id),))
        user_info = cursor.fetchone()
        
        first_name = user_info[0] if user_info and user_info[0] else "نامشخص"
        username = user_info[1] if user_info and user_info[1] else "ندارد"
        joined_at = user_info[2] if user_info and user_info[2] else datetime.now().isoformat()
        
        try:
            joined_date = datetime.fromisoformat(joined_at).strftime('%Y-%m-%d %H:%M')
        except:
            joined_date = joined_at
        
        user_servers = get_user_servers(user_id)
        active_servers = len(user_servers)
        
        msg = get_message("my_account") or DEFAULT_MESSAGES["my_account"]
        msg = msg.format(
            user_id=user_id,
            first_name=first_name,
            username=f"@{username}" if username != "ندارد" else "ندارد",
            active_servers=active_servers,
            total_servers=active_servers,
            joined_at=joined_date,
            today_count=user_data["daily_count"]
        )
        
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
        bot.answer_callback_query(call.id)
        return
    
    if data == "help":
        msg = get_message("help") or DEFAULT_MESSAGES["help"]
        emoji_id = get_welcome_emoji()
        send_separate_emoji(call.message.chat.id, emoji_id)
        edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
        bot.answer_callback_query(call.id)
        return
    
    # ===== بخش‌های پنل مدیریت =====
    
    if data == "admin_panel" and int(user_id) == OWNER_ID:
        msg = get_message("admin_panel") or DEFAULT_MESSAGES["admin_panel"]
        edit_custom_message(call.message, msg, get_admin_keyboard())
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_stats" and int(user_id) == OWNER_ID:
        total = get_total_servers()
        free = get_free_servers_count()
        used = get_used_servers_count()
        users = len(get_all_users())
        
        cursor.execute("SELECT id, used_by, ping FROM servers")
        servers = cursor.fetchall()
        details = ""
        for i, (sid, used_by, ping) in enumerate(servers, 1):
            status = "آزاد" if used_by is None else f"در اختیار کاربر {used_by}"
            ping_status = f" (پینگ: {ping}ms)" if ping and ping > 0 else ""
            details += f"\n{i}. سرور {sid} - {status}{ping_status}"
        
        msg = get_message("admin_stats") or DEFAULT_MESSAGES["admin_stats"]
        msg = msg.format(total=total, free=free, used=used, users=users, details=details)
        
        edit_custom_message(call.message, msg, get_back_keyboard("admin_panel"))
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_add_servers" and int(user_id) == OWNER_ID:
        msg = get_message("admin_add_prompt") or DEFAULT_MESSAGES["admin_add_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        bot.register_next_step_handler(call.message, process_add_servers, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_remove_server" and int(user_id) == OWNER_ID:
        cursor.execute("SELECT id, used_by FROM servers")
        servers = cursor.fetchall()
        
        if not servers:
            edit_custom_message(call.message, "📭 هیچ سروری برای حذف وجود نداره!", get_back_keyboard("admin_panel"))
            bot.answer_callback_query(call.id)
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for sid, used_by in servers:
            status = "آزاد" if used_by is None else f"مشغول ({used_by})"
            keyboard.add(
                InlineKeyboardButton(f"🗑 سرور {sid} - {status}", callback_data=f"remove_server_{sid}")
            )
        keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
        
        msg = get_message("admin_remove_prompt") or DEFAULT_MESSAGES["admin_remove_prompt"]
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("remove_server_") and int(user_id) == OWNER_ID:
        server_id = int(data.split("_")[2])
        remove_server(server_id)
        
        msg = get_message("admin_remove_success") or DEFAULT_MESSAGES["admin_remove_success"]
        msg = msg.format(id=server_id)
        
        edit_custom_message(call.message, msg, get_back_keyboard("admin_panel"))
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_users" and int(user_id) == OWNER_ID:
        users = get_all_users()
        
        if not users:
            edit_custom_message(call.message, "📭 هیچ کاربری ثبت نشده!", get_back_keyboard("admin_panel"))
            bot.answer_callback_query(call.id)
            return
        
        users_text = ""
        for uid, daily_count, servers, first_name, username, joined_at in users:
            try:
                servers_list = json.loads(servers) if servers else []
            except:
                servers_list = eval(servers) if servers else []
            users_text += f"🆔 `{uid}` - {first_name or 'بدون نام'} (@{username or 'بدون یوزر'}) - {len(servers_list)} سرور\n"
        
        msg = get_message("admin_users_list") or DEFAULT_MESSAGES["admin_users_list"]
        msg = msg.format(users=users_text)
        
        if len(msg) > 4000:
            with open("users_list.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            bot.send_document(
                call.message.chat.id,
                open("users_list.txt", "rb"),
                caption="📋 لیست کامل کاربران",
                reply_markup=get_back_keyboard("admin_panel")
            )
            os.remove("users_list.txt")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            edit_custom_message(call.message, msg, get_back_keyboard("admin_panel"))
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_edit_messages" and int(user_id) == OWNER_ID:
        messages = []
        for name in USER_MESSAGE_NAMES:
            text = get_message(name)
            if text is None:
                save_message(name, DEFAULT_MESSAGES.get(name, ""))
                text = get_message(name)
            messages.append((name, text))
        
        total_pages = (len(messages) + EDIT_PAGE_SIZE - 1) // EDIT_PAGE_SIZE
        current_page = 0
        
        edit_page_data[user_id] = {
            "messages": messages,
            "total_pages": total_pages,
            "current_page": current_page
        }
        
        show_edit_page(call.message, user_id, current_page)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("edit_page_") and int(user_id) == OWNER_ID:
        page = int(data.split("_")[2])
        
        data = edit_page_data.get(user_id)
        if data:
            data["current_page"] = page
            show_edit_page(call.message, user_id, page)
        
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("edit_msg_") and int(user_id) == OWNER_ID:
        msg_name = data.replace("edit_msg_", "")
        context["editing_msg_name"] = msg_name
        
        msg = get_message("admin_edit_prompt") or DEFAULT_MESSAGES["admin_edit_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_edit_messages")
        )
        bot.register_next_step_handler(call.message, process_edit_message, msg_name, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_ping_reports" and int(user_id) == OWNER_ID:
        reports = get_pending_ping_reports()
        
        if not reports:
            edit_custom_message(
                call.message,
                "📊 هیچ گزارش پینگ بالایی وجود ندارد!",
                get_back_keyboard("admin_panel")
            )
            bot.answer_callback_query(call.id)
            return
        
        reports_text = ""
        for report_id, server_id, user_id, ping, reported_at, status in reports:
            reports_text += f"\n🆔 سرور: {server_id}\n👤 کاربر: {user_id}\n📊 پینگ: {ping}ms\n⏰ زمان: {reported_at}\n{'-'*30}"
        
        msg = get_message("ping_reports_list") or DEFAULT_MESSAGES["ping_reports_list"]
        msg = msg.format(reports=reports_text)
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("✅ تایید همه", callback_data="confirm_all_pings"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
        )
        
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data == "confirm_all_pings" and int(user_id) == OWNER_ID:
        cursor.execute("UPDATE ping_reports SET status='confirmed'")
        db.commit()
        edit_custom_message(
            call.message,
            "✅ همه گزارش‌های پینگ تایید شدند!",
            get_back_keyboard("admin_panel")
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_update_service" and int(user_id) == OWNER_ID:
        msg = get_message("update_service_prompt") or DEFAULT_MESSAGES["update_service_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_panel")
        )
        bot.register_next_step_handler(call.message, process_update_service, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_server_reports" and int(user_id) == OWNER_ID:
        reports = get_pending_server_reports()
        
        if not reports:
            edit_custom_message(
                call.message,
                "📊 هیچ گزارش خرابی وجود ندارد!",
                get_back_keyboard("admin_panel")
            )
            bot.answer_callback_query(call.id)
            return
        
        reports_text = ""
        for report_id, server_id, user_id, report_text, reported_at, status in reports:
            reports_text += f"\n🆔 سرور: {server_id}\n👤 کاربر: {user_id}\n📝 گزارش: {report_text}\n⏰ زمان: {reported_at}\n{'-'*30}"
        
        msg = get_message("server_reports_list") or DEFAULT_MESSAGES["server_reports_list"]
        msg = msg.format(reports=reports_text)
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("✅ بررسی شد", callback_data="confirm_all_reports"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
        )
        
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data == "confirm_all_reports" and int(user_id) == OWNER_ID:
        cursor.execute("UPDATE server_reports SET status='resolved'")
        db.commit()
        edit_custom_message(
            call.message,
            "✅ همه گزارش‌ها بررسی شدند!",
            get_back_keyboard("admin_panel")
        )
        bot.answer_callback_query(call.id)
        return
    
    # ===== بخش مدیریت چنل‌های اجباری =====
    if data == "admin_required_channels" and int(user_id) == OWNER_ID:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("➕ افزودن چنل جدید", callback_data="add_required_channel"),
            InlineKeyboardButton("📋 لیست چنل‌ها", callback_data="list_required_channels"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
        )
        
        msg = "📢 **مدیریت چنل‌های اجباری**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data == "add_required_channel" and int(user_id) == OWNER_ID:
        channels = get_required_channels()
        if len(channels) >= 10:
            edit_custom_message(
                call.message,
                "❌ **حداکثر ۱۰ چنل قابل اضافه شدن است!**\n\nلطفاً ابتدا یک چنل را حذف کنید.",
                get_back_keyboard("admin_required_channels")
            )
            bot.answer_callback_query(call.id, "❌ حداکثر ۱۰ چنل!", show_alert=True)
            return
        
        msg = get_message("required_channels_prompt") or DEFAULT_MESSAGES["required_channels_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_required_channels")
        )
        bot.register_next_step_handler(call.message, process_add_required_channel, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "list_required_channels" and int(user_id) == OWNER_ID:
        channels = get_required_channels()
        
        if not channels:
            edit_custom_message(
                call.message,
                "📢 **هیچ چنل اجباری تنظیم نشده است!**\n\nبرای افزودن چنل از دکمه زیر استفاده کنید.",
                get_back_keyboard("admin_required_channels")
            )
            bot.answer_callback_query(call.id)
            return
        
        channels_text = ""
        for i, ch in enumerate(channels, 1):
            channels_text += f"{i}. @{ch}\n"
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(channels):
            keyboard.add(
                InlineKeyboardButton(f"🗑 حذف @{ch}", callback_data=f"remove_channel_{ch}")
            )
        keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_required_channels"))
        
        msg = get_message("required_channels_list") or DEFAULT_MESSAGES["required_channels_list"]
        msg = msg.format(channels=channels_text, count=len(channels))
        
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("remove_channel_") and int(user_id) == OWNER_ID:
        channel = data.replace("remove_channel_", "")
        channels = get_required_channels()
        
        if channel in channels:
            channels.remove(channel)
            set_required_channels(channels)
            
            msg = get_message("required_channel_removed") or DEFAULT_MESSAGES["required_channel_removed"]
            msg = msg.format(channel=channel)
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📋 لیست چنل‌ها", callback_data="list_required_channels"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_required_channels")
            )
            
            edit_custom_message(call.message, msg, keyboard)
            bot.answer_callback_query(call.id, f"✅ چنل @{channel} حذف شد!", show_alert=True)
        else:
            edit_custom_message(
                call.message,
                "❌ چنل مورد نظر یافت نشد!",
                get_back_keyboard("admin_required_channels")
            )
            bot.answer_callback_query(call.id)
        return
    
    if data == "admin_broadcast" and int(user_id) == OWNER_ID:
        msg = get_message("admin_broadcast_prompt") or DEFAULT_MESSAGES["admin_broadcast_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_panel")
        )
        bot.register_next_step_handler(call.message, process_broadcast, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_set_emoji" and int(user_id) == OWNER_ID:
        msg = get_message("admin_set_emoji_prompt") or DEFAULT_MESSAGES["admin_set_emoji_prompt"]
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_keyboard("admin_panel")
        )
        bot.register_next_step_handler(call.message, process_set_emoji, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "admin_delete_db" and int(user_id) == OWNER_ID:
        msg = get_message("admin_delete_db_confirm") or DEFAULT_MESSAGES["admin_delete_db_confirm"]
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ بله، حذف شود", callback_data="confirm_delete_db"),
            InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")
        )
        edit_custom_message(call.message, msg, keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data == "confirm_delete_db" and int(user_id) == OWNER_ID:
        try:
            if os.path.exists("bot.db"):
                os.remove("bot.db")
            
            msg = get_message("admin_delete_db_success") or DEFAULT_MESSAGES["admin_delete_db_success"]
            edit_custom_message(call.message, msg, get_back_keyboard("back_to_main"))
            bot.answer_callback_query(call.id, "✅ دیتابیس حذف شد! ربات را مجدداً راه‌اندازی کنید.", show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا در حذف دیتابیس: {str(e)}", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)

# ==================== تابع نمایش صفحه ویرایش ====================

def show_edit_page(message, user_id, page):
    data = edit_page_data.get(user_id)
    if not data:
        return
    
    messages = data["messages"]
    total_pages = data["total_pages"]
    start_idx = page * EDIT_PAGE_SIZE
    end_idx = min(start_idx + EDIT_PAGE_SIZE, len(messages))
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for name, text in messages[start_idx:end_idx]:
        display_name = name.replace("_", " ").title()
        keyboard.add(
            InlineKeyboardButton(f"✏️ {display_name}", callback_data=f"edit_msg_{name}")
        )
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"edit_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"edit_page_{page+1}"))
    
    if nav_buttons:
        keyboard.add(*nav_buttons)
    
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
    
    msg = get_message("admin_edit_messages") or DEFAULT_MESSAGES["admin_edit_messages"]
    msg += f"\n\n📄 صفحه {page+1} از {total_pages}"
    
    edit_custom_message(message, msg, keyboard)

# ==================== هندلرهای مرحله به مرحله ====================

def process_rename(message, server_id, original_msg):
    user_id = message.from_user.id
    
    if message.text.lower() == "/cancel":
        emoji_id = get_welcome_emoji()
        send_separate_emoji(message.chat.id, emoji_id)
        send_custom_message(message.chat.id, "❌ عملیات تغییر نام لغو شد.", get_main_keyboard(user_id), send_emoji_first=False)
        return
    
    new_name = message.text.strip()
    
    if not new_name:
        emoji_id = get_welcome_emoji()
        send_separate_emoji(message.chat.id, emoji_id)
        send_custom_message(
            message.chat.id,
            "❌ نام نمی‌تواند خالی باشد!\nلطفاً دوباره تلاش کنید.",
            get_main_keyboard(user_id),
            send_emoji_first=False
        )
        return
    
    user_servers = get_user_servers(user_id)
    
    found = False
    for server in user_servers:
        if server["server_id"] == server_id:
            server["name"] = new_name
            found = True
            break
    
    if not found:
        emoji_id = get_welcome_emoji()
        send_separate_emoji(message.chat.id, emoji_id)
        send_custom_message(
            message.chat.id,
            "❌ سرور مورد نظر یافت نشد!",
            get_main_keyboard(user_id),
            send_emoji_first=False
        )
        return
    
    save_user_servers(user_id, user_servers)
    
    msg = get_message("rename_confirmed") or DEFAULT_MESSAGES["rename_confirmed"]
    msg = msg.format(new_name=new_name)
    
    emoji_id = get_welcome_emoji()
    send_separate_emoji(message.chat.id, emoji_id)
    send_custom_message(
        message.chat.id, 
        msg, 
        get_back_keyboard("my_services"),
        send_emoji_first=False
    )

def process_add_servers(message, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات افزودن سرور لغو شد.", get_main_keyboard(user_id))
        return
    
    configs = [line.strip() for line in message.text.split('\n') if line.strip()]
    
    if not configs:
        send_custom_message(
            message.chat.id,
            "❌ هیچ کانفیگ معتبری یافت نشد!\nلطفاً دوباره تلاش کنید.",
            get_main_keyboard(user_id)
        )
        return
    
    added = 0
    for config in configs:
        ip = "Unknown"
        port = "Unknown"
        try:
            if "@" in config:
                parts = config.split("@")
                if len(parts) > 1:
                    ip_port = parts[1].split("?")[0].split(":")
                    if len(ip_port) >= 2:
                        ip = ip_port[0]
                        port = ip_port[1]
        except:
            pass
        
        add_server(config, ip, port)
        added += 1
    
    msg = get_message("admin_add_success") or DEFAULT_MESSAGES["admin_add_success"]
    msg = msg.format(
        count=added,
        total=get_total_servers(),
        id_range=f"{get_total_servers() - added + 1} تا {get_total_servers()}"
    )
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 مشاهده آمار", callback_data="admin_stats"),
        InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")
    )
    
    send_custom_message(message.chat.id, msg, keyboard)

def process_add_required_channel(message, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات لغو شد.", get_main_keyboard(user_id))
        return
    
    channel = message.text.strip().replace("@", "").strip()
    
    if not channel:
        send_custom_message(
            message.chat.id,
            "❌ یوزرنیم چنل معتبر نیست!\nلطفاً دوباره تلاش کنید.",
            get_main_keyboard(user_id)
        )
        return
    
    channels = get_required_channels()
    
    if len(channels) >= 10:
        send_custom_message(
            message.chat.id,
            "❌ **حداکثر ۱۰ چنل قابل اضافه شدن است!**\n\nلطفاً ابتدا یک چنل را حذف کنید.",
            get_back_keyboard("admin_required_channels")
        )
        return
    
    if channel in channels:
        send_custom_message(
            message.chat.id,
            f"❌ چنل @{channel} قبلاً اضافه شده است!",
            get_back_keyboard("admin_required_channels")
        )
        return
    
    try:
        bot.get_chat_member(f"@{channel}", bot.get_me().id)
    except:
        send_custom_message(
            message.chat.id,
            f"❌ **ربات ادمین چنل @{channel} نیست!**\n\nلطفاً ابتدا ربات را ادمین چنل کنید.",
            get_back_keyboard("admin_required_channels")
        )
        return
    
    channels.append(channel)
    set_required_channels(channels)
    
    channels_text = "\n".join([f"• @{ch}" for ch in channels])
    msg = get_message("required_channels_set") or DEFAULT_MESSAGES["required_channels_set"]
    msg = msg.format(channels=channels_text)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📋 لیست چنل‌ها", callback_data="list_required_channels"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="admin_required_channels")
    )
    
    send_custom_message(message.chat.id, msg, keyboard)

def process_edit_message(message, msg_name, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات ویرایش لغو شد.", get_main_keyboard(user_id))
        return
    
    save_message(msg_name, message.text)
    
    msg = get_message("admin_edit_success") or DEFAULT_MESSAGES["admin_edit_success"]
    send_custom_message(message.chat.id, msg, get_back_keyboard("admin_edit_messages"))

def process_update_service(message, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات آپدیت لغو شد.", get_main_keyboard(user_id))
        return
    
    if "|" not in message.text:
        send_custom_message(
            message.chat.id,
            "❌ فرمت ورودی صحیح نیست!\nلطفاً به فرمت `سرور_آی‌دی|کانفیگ_جدید` ارسال کنید.",
            get_main_keyboard(user_id)
        )
        return
    
    try:
        server_id_str, new_config = message.text.split("|", 1)
        server_id = int(server_id_str.strip())
        new_config = new_config.strip()
        
        server = get_server_by_id(server_id)
        if not server:
            send_custom_message(
                message.chat.id,
                f"❌ سرور با آی‌دی {server_id} یافت نشد!",
                get_main_keyboard(user_id)
            )
            return
        
        user_id_of_server = server[5]
        if not user_id_of_server:
            send_custom_message(
                message.chat.id,
                f"❌ سرور {server_id} به هیچ کاربری اختصاص داده نشده!",
                get_main_keyboard(user_id)
            )
            return
        
        update_server_config(server_id, new_config)
        
        user_servers = get_user_servers(user_id_of_server)
        for s in user_servers:
            if s["server_id"] == server_id:
                hashtag = ""
                if " " in s["config"]:
                    hashtag = s["config"].split(" ")[-1] if s["config"].split(" ")[-1].startswith("#") else ""
                elif "#" in s["config"]:
                    hashtag_match = re.search(r'#\S+', s["config"])
                    if hashtag_match:
                        hashtag = hashtag_match.group()
                
                if hashtag:
                    new_config_with_hashtag = f"{new_config} {hashtag}"
                else:
                    username = f"user{user_id_of_server}"
                    new_config_with_hashtag = add_hashtag_to_config(new_config, user_id_of_server, username)
                
                s["config"] = new_config_with_hashtag
                break
        
        save_user_servers(user_id_of_server, user_servers)
        
        update_msg = get_message("server_updated_notification") or DEFAULT_MESSAGES["server_updated_notification"]
        update_msg = update_msg.format(server_name=f"سرور {server_id}")
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("📋 سرویس‌های من", callback_data="my_services")
        )
        
        send_custom_message(int(user_id_of_server), update_msg, keyboard)
        
        send_custom_message(
            message.chat.id,
            f"✅ سرویس سرور {server_id} با موفقیت آپدیت شد!\nکاربر {user_id_of_server} مطلع شد.",
            get_main_keyboard(user_id)
        )
        
    except ValueError:
        send_custom_message(
            message.chat.id,
            "❌ آی‌دی سرور باید عدد باشد!\nلطفاً به فرمت `سرور_آی‌دی|کانفیگ_جدید` ارسال کنید.",
            get_main_keyboard(user_id)
        )
    except Exception as e:
        send_custom_message(
            message.chat.id,
            f"❌ خطا در آپدیت سرویس: {str(e)}",
            get_main_keyboard(user_id)
        )

def process_server_report(message, server_id, original_msg):
    user_id = message.from_user.id
    
    if message.text.lower() == "/cancel":
        emoji_id = get_welcome_emoji()
        send_separate_emoji(message.chat.id, emoji_id)
        send_custom_message(message.chat.id, "❌ عملیات گزارش لغو شد.", get_main_keyboard(user_id), send_emoji_first=False)
        return
    
    report_text = message.text
    
    save_server_report(server_id, user_id, report_text)
    
    msg = get_message("report_sent") or DEFAULT_MESSAGES["report_sent"]
    msg = msg.format(
        server_name=f"سرور {server_id}",
        report_text=report_text
    )
    
    emoji_id = get_welcome_emoji()
    send_separate_emoji(message.chat.id, emoji_id)
    send_custom_message(message.chat.id, msg, get_back_keyboard("my_services"), send_emoji_first=False)
    
    owner_msg = get_message("admin_report_notification") or DEFAULT_MESSAGES["admin_report_notification"]
    owner_msg = owner_msg.format(
        server_id=server_id,
        user_id=user_id,
        report_text=report_text,
        time=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    
    bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")

def process_broadcast(message, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات لغو شد.", get_main_keyboard(user_id))
        return
    
    users = get_all_users()
    success_count = 0
    fail_count = 0
    
    is_forwarded = hasattr(message, 'forward_from_chat') or hasattr(message, 'forward_from')
    
    for user in users:
        try:
            user_id_send = int(user[0])
            
            if is_forwarded:
                bot.forward_message(
                    user_id_send,
                    message.chat.id,
                    message.message_id
                )
            else:
                text = message.text or message.caption or ""
                if text:
                    send_custom_message(user_id_send, text)
                else:
                    if message.photo:
                        bot.send_photo(user_id_send, message.photo[-1].file_id, caption=message.caption)
                    elif message.document:
                        bot.send_document(user_id_send, message.document.file_id, caption=message.caption)
                    elif message.video:
                        bot.send_video(user_id_send, message.video.file_id, caption=message.caption)
                    elif message.audio:
                        bot.send_audio(user_id_send, message.audio.file_id, caption=message.caption)
                    elif message.voice:
                        bot.send_voice(user_id_send, message.voice.file_id)
            
            success_count += 1
            time.sleep(0.05)
        except Exception as e:
            fail_count += 1
            print(f"Error sending to {user[0]}: {e}")
    
    msg = get_message("admin_broadcast_success") or DEFAULT_MESSAGES["admin_broadcast_success"]
    if is_forwarded:
        text_display = "📎 پیام فوروارد شده"
    else:
        text_display = message.text or "📎 پیام غیرمتنی"
    
    msg = msg.format(count=success_count, text=text_display)
    
    if fail_count > 0:
        msg += f"\n\n⚠️ {fail_count} نفر دریافت نکردند."
    
    send_custom_message(
        message.chat.id,
        msg,
        get_main_keyboard(user_id)
    )

def process_set_emoji(message, original_msg):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        send_custom_message(message.chat.id, "❌ عملیات لغو شد.", get_main_keyboard(user_id))
        return
    
    emoji_id = message.text.strip()
    
    if not emoji_id or not emoji_id.isdigit():
        send_custom_message(
            message.chat.id,
            "❌ کد ایموجی معتبر نیست!\nلطفاً یک کد عددی معتبر وارد کنید.",
            get_main_keyboard(user_id)
        )
        return
    
    set_welcome_emoji(emoji_id)
    
    msg = get_message("admin_set_emoji_success") or DEFAULT_MESSAGES["admin_set_emoji_success"]
    msg = msg.format(emoji_id=emoji_id)
    
    send_custom_message(
        message.chat.id,
        msg,
        get_back_keyboard("admin_panel")
    )

# ==================== اجرای اصلی ====================

print("=" * 50)
print("🤖 ربات با موفقیت راه‌اندازی شد!")
print(f"👤 مالک: {OWNER_ID}")
print(f"📊 تعداد سرورهای موجود: {get_total_servers()}")
print(f"👥 تعداد کاربران: {len(get_all_users())}")
print(f"⏱ زمان بررسی پینگ: هر {PING_INTERVAL} ثانیه")
print(f"📊 آستانه پینگ: {PING_THRESHOLD} ms")
print("=" * 50)

start_ping_scheduler()

bot.infinity_polling()
