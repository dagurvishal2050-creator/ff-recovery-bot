import os
import sqlite3
import logging
from datetime import datetime, timezone

import telebot
from telebot import types

# Environment variables required:
# BOT_TOKEN=your_telegram_bot_token
# ADMIN_IDS=123456789,987654321
# DB_PATH=bot.sqlite3 (optional)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
DB_PATH = os.getenv("DB_PATH", "bot.sqlite3")

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in your environment.")
if not ADMIN_IDS:
    raise RuntimeError("Set ADMIN_IDS to at least one Telegram numeric user ID.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
logging.basicConfig(level=logging.INFO)

# In-memory conversation states. For high-volume production use, persist states in DB.
states = {}
drafts = {}

PLANS = {
    "Basic": {"price": "Set your Basic price"},
    "Premium": {"price": "Set your Premium price"},
}
SERVICES = ["Mail Unlink", "Unlink + Relink"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                name TEXT,
                game_uid TEXT,
                mobile TEXT,
                email TEXT,
                login_method TEXT,
                login_username TEXT,
                plan TEXT,
                service TEXT,
                price TEXT,
                payment_reference TEXT,
                amount TEXT,
                receipt_file_id TEXT,
                payment_status TEXT DEFAULT 'Not Received',
                created_at TEXT NOT NULL
            )
        """)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Basic Plan", "Premium Plan")
    kb.row("Help / Contact Support")
    return kb

def ask_next(chat_id, user_id, prompt, state):
    states[user_id] = state
    bot.send_message(chat_id, prompt, reply_markup=types.ReplyKeyboardRemove())

def start_request(message, plan):
    uid = message.from_user.id
    drafts[uid] = {
        "user_id": uid,
        "username": message.from_user.username or "",
        "plan": plan,
        "price": PLANS[plan]["price"],
    }
    ask_next(message.chat.id, uid, "Enter your name:", "name")

def send_admin_request(request_id):
    with db() as conn:
        r = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
    if not r:
        return

    # First admin message: basic details and plan.
    basic = (
        "📋 <b>New Support Request — Basic Details</b>\n"
        f"User ID: <code>{r['user_id']}</code>\n"
        f"Name: {html_escape(r['name'])}\n"
        f"Game UID: {html_escape(r['game_uid'])}\n"
        f"Mobile: {html_escape(r['mobile'])}\n"
        f"Email: {html_escape(r['email'])}\n"
        f"Login method: {html_escape(r['login_method'])}\n"
        f"Username/Mobile: {html_escape(r['login_username'])}\n"
        "Password: <b>Not collected</b>\n\n"
        f"Plan: {html_escape(r['plan'])}\n"
        f"Service: {html_escape(r['service'])}\n"
        f"Price: {html_escape(r['price'])}\n"
        f"Request Ref (admin only): <code>{r['id']}</code>"
    )
    # Second admin message: payment proof/reference.
    payment = (
        "💳 <b>Payment Details</b>\n"
        f"User ID: <code>{r['user_id']}</code>\n"
        f"Name: {html_escape(r['name'])}\n"
        f"Payment reference: {html_escape(r['payment_reference'])}\n"
        f"Amount: {html_escape(r['amount'])}\n"
        f"Payment status: <b>{html_escape(r['payment_status'])}</b>\n"
        "Verify the payment using the issuer/provider's official records."
    )
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Received", callback_data=f"pay:received:{r['id']}"),
        types.InlineKeyboardButton("❌ Not Received", callback_data=f"pay:not_received:{r['id']}")
    )

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, basic)
            # Keep payment details and receipt together as the second admin message.
            if r["receipt_file_id"]:
                try:
                    bot.send_photo(admin_id, r["receipt_file_id"], caption=payment, reply_markup=kb)
                except Exception:
                    bot.send_document(admin_id, r["receipt_file_id"], caption=payment, reply_markup=kb)
            else:
                bot.send_message(admin_id, payment, reply_markup=kb)
        except Exception:
            logging.exception("Could not deliver request to admin %s", admin_id)

def html_escape(value):
    from html import escape
    return escape(str(value or "—"))

@bot.message_handler(commands=["start"])
def cmd_start(message):
    states.pop(message.from_user.id, None)
    drafts.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Welcome to Support Intake.\n\n"
        "Choose a plan to submit a request, or choose Help to contact support.\n"
        "Never send your account password, one-time code, or gift-card PIN.",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    states.pop(message.from_user.id, None)
    drafts.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Request cancelled.", reply_markup=main_menu())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    uid = message.from_user.id
    states[uid] = "help"
    bot.send_message(
        message.chat.id,
        "Describe your issue in one message. Do not include passwords, one-time codes, or payment-card PINs.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(commands=["reply"])
def cmd_reply(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Not authorized.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(message, "Usage: /reply USER_ID message")
        return
    target_id = int(parts[1])
    try:
        bot.send_message(target_id, "📩 <b>Support reply</b>\n" + html_escape(parts[2]))
        bot.reply_to(message, "Reply sent.")
    except Exception as e:
        bot.reply_to(message, f"Could not send reply: {html_escape(e)}")

@bot.message_handler(content_types=["text", "photo", "document"], func=lambda m: m.text in ["Basic Plan", "Premium Plan"] if m.content_type == "text" else False)
def plan_selected(message):
    plan = "Basic" if message.text == "Basic Plan" else "Premium"
    start_request(message, plan)

@bot.message_handler(content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    state = states.get(uid)

    if message.text == "Help / Contact Support":
        states[uid] = "help"
        bot.send_message(message.chat.id, "Describe your issue in one message. Do not include passwords, one-time codes, or gift-card PINs.", reply_markup=types.ReplyKeyboardRemove())
        return

    if not state:
        return

    if state == "receipt":
        if message.text.strip().upper() == "SKIP":
            finalize_request(message.chat.id, uid)
        else:
            bot.send_message(message.chat.id, "Upload a receipt/screenshot, or type SKIP.")
        return

    if state == "help":
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    "🆘 <b>Support message</b>\n"
                    f"User ID: <code>{uid}</code>\n"
                    f"Username: @{html_escape(message.from_user.username or 'not set')}\n\n"
                    f"{html_escape(message.text)}"
                )
            except Exception:
                logging.exception("Could not forward help message")
        states.pop(uid, None)
        bot.send_message(message.chat.id, "Your message has been sent to support.", reply_markup=main_menu())
        return

    d = drafts.setdefault(uid, {"user_id": uid, "username": message.from_user.username or ""})
    fields = {
        "name": ("game_uid", "Enter your in-game UID:"),
        "game_uid": ("mobile", "Enter your mobile number, or type SKIP:"),
        "mobile": ("email", "Enter your email address, or type SKIP:"),
        "email": ("login_method", "Enter your login method (Google/Facebook/Apple/Guest/Other):"),
        "login_method": ("login_username", "Enter a contact username/mobile if needed, or type SKIP. Do not enter a password or one-time code:"),
        "login_username": ("service", "Choose service: type Mail Unlink or Unlink + Relink."),
        "service": ("payment_reference", "Enter your payment reference/transaction ID. Do not send a gift-card PIN or account password."),
        "payment_reference": ("amount", "Enter the amount paid (for example, 500):"),
        "amount": ("receipt", "Now upload a receipt/screenshot as a photo or document. If you do not have one, type SKIP."),
    }
    if state == "name":
        d["name"] = message.text.strip()
    elif state in ("game_uid", "mobile", "email", "login_method", "login_username", "service", "payment_reference", "amount"):
        key = state
        value = message.text.strip()
        if value.upper() == "SKIP" and key in ("mobile", "email", "login_username"):
            value = "Not provided"
        if key == "service" and value not in SERVICES:
            bot.send_message(message.chat.id, "Please type exactly: Mail Unlink or Unlink + Relink.")
            return
        d[key] = value
    else:
        return

    next_state, prompt = fields[state]
    if next_state == "service":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row("Mail Unlink", "Unlink + Relink")
        states[uid] = next_state
        bot.send_message(message.chat.id, prompt, reply_markup=kb)
    else:
        ask_next(message.chat.id, uid, prompt, next_state)

@bot.message_handler(content_types=["photo", "document"])
def handle_receipt(message):
    uid = message.from_user.id
    if states.get(uid) != "receipt":
        return
    d = drafts.get(uid)
    if not d:
        states.pop(uid, None)
        bot.send_message(message.chat.id, "Your session expired. Please use /start again.", reply_markup=main_menu())
        return
    if message.content_type == "photo":
        receipt_file_id = message.photo[-1].file_id
    else:
        receipt_file_id = message.document.file_id
    d["receipt_file_id"] = receipt_file_id
    finalize_request(message.chat.id, uid)

def finalize_request(chat_id, uid):
    d = drafts.get(uid, {})
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO requests (
                user_id, username, name, game_uid, mobile, email, login_method,
                login_username, plan, service, price, payment_reference, amount,
                receipt_file_id, payment_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Not Received', ?)
        """, (
            uid, d.get("username", ""), d.get("name", ""),
            d.get("game_uid", ""), d.get("mobile", ""), d.get("email", ""),
            d.get("login_method", ""), d.get("login_username", ""),
            d.get("plan", ""), d.get("service", ""), d.get("price", ""),
            d.get("payment_reference", "Not provided"), d.get("amount", ""),
            d.get("receipt_file_id", ""),
            datetime.now(timezone.utc).isoformat()
        ))
        request_id = cur.lastrowid

    send_admin_request(request_id)
    states.pop(uid, None)
    drafts.pop(uid, None)
    bot.send_message(
        chat_id,
        "✅ Your request has been submitted for review. The support team will verify the payment proof and contact you here.",
        reply_markup=main_menu()
    )

@bot.message_handler(content_types=["text"], func=lambda m: states.get(m.from_user.id) == "receipt")
def skip_receipt(message):
    if message.text.strip().upper() != "SKIP":
        bot.send_message(message.chat.id, "Upload a receipt/screenshot, or type SKIP.")
        return
    finalize_request(message.chat.id, message.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay:"))
def payment_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.", show_alert=True)
        return
    _, status_key, request_id = call.data.split(":")
    status = "Received" if status_key == "received" else "Not Received"
    with db() as conn:
        conn.execute("UPDATE requests SET payment_status=? WHERE id=?", (status, int(request_id)))
        r = conn.execute("SELECT user_id FROM requests WHERE id=?", (int(request_id),)).fetchone()
    bot.answer_callback_query(call.id, f"Marked {status}.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    if r:
        try:
            bot.send_message(r["user_id"], f"Payment status update: <b>{status}</b>")
        except Exception:
            pass

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text and m.text.startswith("/"))
def admin_fallback(message):
    # Leave other admin commands alone; /reply is handled above.
    return

init_db()
print("Support bot is running...")
bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
