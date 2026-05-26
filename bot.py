import os
import time
from flask import Flask, send_from_directory, jsonify, request

import telebot
from telebot import types

APP_URL = "https://ancient-forex-bot.onrender.com"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Flask(__name__)

access_until = {}
trial_used = set()

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return "OK", 200


@app.route("/api/access")
def api_access():
    user = request.args.get("user", "")
    now = int(time.time())
    until = access_until.get(user, 0)

    return jsonify({
        "active": until > now,
        "until": until,
        "seconds_left": max(0, until - now)
    })


def keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎮 OPEN GAME", web_app=types.WebAppInfo(APP_URL + "/")))
    kb.add(types.InlineKeyboardButton("🆓 FREE 5 MIN", callback_data="trial"))
    kb.add(types.InlineKeyboardButton("⭐ 1 HOUR — 50", callback_data="pay1"))
    kb.add(types.InlineKeyboardButton("⭐ 24 HOURS — 150", callback_data="pay24"))
    kb.add(types.InlineKeyboardButton("⭐ 48 HOURS — 300", callback_data="pay48"))
    kb.add(types.InlineKeyboardButton("⏳ MY ACCESS", callback_data="access"))
    return kb


if bot:
    @bot.message_handler(commands=["start"])
    def start(msg):
        bot.send_message(
            msg.chat.id,
            """🃏 Ancient Card Games

🎮 Ancient Poker
🂡 Emperor's 21
🃏 Joker Duel

🆓 5 minutes free
⭐ 1 hour — 50 Stars
⭐ 24 hours — 150 Stars
⭐ 48 hours — 300 Stars

Training & entertainment only.
No real money. No gambling. No withdrawals.""",
            reply_markup=keyboard()
        )


    @bot.callback_query_handler(func=lambda c: c.data == "trial")
    def trial(call):
        user = str(call.from_user.id)

        if user in trial_used:
            bot.answer_callback_query(call.id, "Trial already used")
            return

        trial_used.add(user)
        access_until[user] = int(time.time()) + 300

        bot.answer_callback_query(call.id, "5 minutes activated")
        bot.send_message(call.message.chat.id, "🆓 Trial unlocked for 5 minutes.", reply_markup=keyboard())


    @bot.callback_query_handler(func=lambda c: c.data == "access")
    def my_access(call):
        user = str(call.from_user.id)
        now = int(time.time())
        until = access_until.get(user, 0)

        if until > now:
            minutes = (until - now) // 60
            bot.answer_callback_query(call.id, f"Access active: {minutes} min left")
            bot.send_message(call.message.chat.id, f"✅ Access active. Time left: {minutes} minutes.")
        else:
            bot.answer_callback_query(call.id, "No active access")
            bot.send_message(call.message.chat.id, "❌ No active access.", reply_markup=keyboard())


    @bot.callback_query_handler(func=lambda c: c.data in ["pay1", "pay24", "pay48"])
    def pay(call):
        plans = {
            "pay1": (50, "1h"),
            "pay24": (150, "24h"),
            "pay48": (300, "48h")
        }

        stars, payload = plans[call.data]

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title="Ancient Card Games",
            description="Game access",
            invoice_payload=payload,
            currency="XTR",
            provider_token="",
            prices=[types.LabeledPrice("Access", stars)]
        )

        bot.answer_callback_query(call.id)


    @bot.pre_checkout_query_handler(func=lambda q: True)
    def checkout(q):
        bot.answer_pre_checkout_query(q.id, ok=True)


    @bot.message_handler(content_types=["successful_payment"])
    def paid(msg):
        payload = msg.successful_payment.invoice_payload
        now = int(time.time())
        user = str(msg.from_user.id)

        if payload == "1h":
            access_until[user] = now + 3600
        elif payload == "24h":
            access_until[user] = now + 86400
        elif payload == "48h":
            access_until[user] = now + 172800

        bot.send_message(msg.chat.id, "✅ Access activated.", reply_markup=keyboard())


@app.route("/webhook", methods=["POST"])
def webhook():
    if not bot:
        return "BOT_TOKEN missing", 500

    update = types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200


def setup_webhook():
    if not bot:
        print("BOT_TOKEN is missing.")
        return

    bot.remove_webhook()
    time.sleep(1)
    webhook_url = APP_URL + "/webhook"
    bot.set_webhook(url=webhook_url)
    print("Webhook set:", webhook_url)


if __name__ == "__main__":
    setup_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
