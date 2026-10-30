import os
import random
import string
from flask import Flask, request, render_template_string
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "9015143190:AAGaL2nkNpxlK6_1zutMDQdSU4YR6TNp1hk"
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)
user_states = {}

def generate_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

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

# Mini App ke liye Home Route (Jo Telegram Mini App mein khulega)
@app.route('/')
def index():
    html_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FF Recovery Mini App</title>
        <style>
            body { background-color: #0f172a; color: #ffffff; font-family: Arial, sans-serif; text-align: center; padding: 20px; }
            .container { max-width: 400px; margin: auto; background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            input, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: none; font-size: 16px; }
            input { background: #334155; color: white; }
            button { background: #2563eb; color: white; font-weight: bold; cursor: pointer; }
            button:hover { background: #1d4ed8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🛡️ Free Fire Recovery</h2>
            <p>Apne account ki details yahan darj karein:</p>
            <input type="text" id="uid" placeholder="Enter Player UID">
            <input type="text" id="ign" placeholder="Enter In-Game Name (IGN)">
            <input type="text" id="payment" placeholder="Transaction ID / Payment Details">
            <button onclick="submitData()">Submit Request</button>
        </div>
        <script>
            function submitData() {
                const uid = document.getElementById('uid').value;
                const ign = document.getElementById('ign').value;
                const payment = document.getElementById('payment').value;
                if(!uid || !ign || !payment) {
                    alert('Kripya sabhi fields bharein!');
                    return;
                }
                alert('Request submitted successfully! Bot par wapas jayein.');
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_page)

# Telegram Bot /start command
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 Open Recovery Mini App", web_app=telebot.types.WebAppInfo(url="https://ff-recovery-bot.onrender.com/")))
    bot.send_message(
        chat_id, 
        "Welcome to **Free Fire ID Recovery Support Bot**! 🛡️\n\nNiche diye gaye button par click karke Mini App kholein:", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
