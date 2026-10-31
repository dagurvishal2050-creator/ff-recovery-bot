# Telegram Support Bot Starter

## Features
- Basic/Premium plan selection
- Collects name, in-game UID, contact details, login method, service and plan
- Does **not** collect account passwords, OTPs, or gift-card PINs
- Payment proof uses a transaction/reference ID, amount and optional receipt
- Sends two main admin messages per request (basic details and payment details); receipt file is forwarded separately if uploaded
- Admin-only `Received` / `Not Received` buttons
- Admin command: `/reply USER_ID message`
- `/help` forwards a user's issue to admins with their Telegram User ID
- SQLite persistence for requests

## Setup
1. Create a bot with Telegram's official BotFather and copy the token.
2. Find your numeric Telegram user ID and configure it as an admin.
3. Install Python 3.10+.
4. Run:

   ```bash
   pip install -r requirements.txt
   export BOT_TOKEN="YOUR_NEW_BOT_TOKEN"
   export ADMIN_IDS="123456789"
   python app.py
   ```

   On Windows PowerShell:

   ```powershell
   $env:BOT_TOKEN="YOUR_NEW_BOT_TOKEN"
   $env:ADMIN_IDS="123456789"
   python app.py
   ```

5. Keep the process running. For hosting, use a persistent disk for `bot.sqlite3`.

## Before going live
- Replace `Set your Basic price` and `Set your Premium price` in `app.py` with your real prices.
- Add a privacy notice and only collect data you actually need.
- Verify payments with the payment provider's official records. A screenshot alone is not proof of settlement.
- Never ask users to send account passwords, OTPs, or gift-card PINs.
- Do not represent this bot as an official game publisher support channel unless you are authorized.
- Rotate any bot token previously pasted into chats or shared publicly.
