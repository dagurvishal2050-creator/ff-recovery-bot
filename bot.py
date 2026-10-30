import os
import random
import string
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Apka Bot Token
TOKEN = "9015143190:AAGaL2nkNpxlK6_1zutMDQdSU4YR6TNp1hk"
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# User recovery states ko track karne ke liye dictionary
user_states = {}

def generate_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# Webhook route (Flask ka built-in request.json use kiya hai taaki request miss na ho)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.json
        if json_data:
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

# Basic home route
@app.route('/')
def index():
    return "FF Recovery Bot is live and running successfully!"

# /start command handler
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Start Free Fire Recovery", callback_data="start_recovery"))
    bot.send_message(
        chat_id, 
        "Welcome to **Free Fire ID Recovery Support Bot**! 🛡️\n\nAap apne account ko recover karne ke liye niche diye gaye button par click karein.", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

# Recovery process shuru karne ka callback
@bot.callback_query_handler(func=lambda call: call.data == "start_recovery")
def recovery_callback(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = {"step": "get_uid"}
    bot.answer_callback_query(call.id)
    bot.send_message(chat_id, "Kripya apne Free Fire ka **UID (Player ID)** enter karein:")

# Step-by-step user input handler
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_recovery_steps(message):
    chat_id = message.chat.id
    state = user_states[chat_id].get("step")

    if state == "get_uid":
        user_states[chat_id]["uid"] = message.text.strip()
        user_states[chat_id]["step"] = "get_ign"
        bot.send_message(chat_id, "Bohot badhiya! Ab apna In-Game Name (**IGN**) enter karein:")

    elif state == "get_ign":
        user_states[chat_id]["ign"] = message.text.strip()
        user_states[chat_id]["step"] = "get_payment"
        bot.send_message(chat_id, "Ab apni payment ka **Transaction ID / Screenshot details** bhejein taaki verification ho sake:")

    elif state == "get_payment":
        payment_info = message.text.strip()
        ticket_id = f"FF-{generate_ticket_id()}"
        uid = user_states[chat_id].get("uid")
        ign = user_states[chat_id].get("ign")
        username = message.from_user.username or message.from_user.first_name

        # User ka state clear kar do
        del user_states[chat_id]

        # User ko confirmation bhejo
        bot.send_message(
            chat_id, 
            f"✅ Aapki recovery request successfully submit ho gayi hai!\n\n🎟️ **Ticket ID:** `{ticket_id}`\n👤 **UID:** `{uid}`\n🏷️ **IGN:** `{ign}`\n\nAdmin jald hi aapki request verify karenge.", 
            parse_mode="Markdown"
        )

        # Admin ke liye approval buttons wala message (Yahi chat ya admin chat par jayega)
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{ticket_id}_{chat_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{ticket_id}_{chat_id}")
        )
        
        bot.send_message(
            chat_id, 
            f"🚨 **New Recovery Request!**\n\n🎟️ **Ticket:** `{ticket_id}`\n👤 **User:** @{username} (`{chat_id}`)\n🆔 **UID:** `{uid}`\n🏷️ **IGN:** `{ign}`\n💳 **Payment:** {payment_info}", 
            parse_mode="Markdown", 
            reply_markup=markup
        )

# Admin Action (Approve / Reject) Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_action(call):
    data_parts = call.data.split("_")
    action = data_parts[0]
    ticket_id = data_parts[1]
    target_chat_id = data_parts[2]

    bot.answer_callback_query(call.id)

    if action == "approve":
        bot.send_message(target_chat_id, f"🎉 Badhai ho! Aapki recovery ticket `{ticket_id}` **Approve** ho chuki hai.", parse_mode="Markdown")
        bot.edit_message_text(f"✅ Approved Request (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.send_message(target_chat_id, f"❌ Maaf kijiyega, aapki recovery ticket `{ticket_id}` **Reject** kar di gayi hai.", parse_mode="Markdown")
        bot.edit_message_text(f"❌ Rejected Request (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
