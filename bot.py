import os
import time
import threading
from flask import Flask, send_from_directory, jsonify, request

try:
    import telebot
    from telebot import types
except Exception:
    telebot = None
    types = None

APP_URL = "https://ancient-forex-bot.onrender.com/"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Flask(__name__)
access_until = {}

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return "OK", 200

@app.route("/api/access")
def api_access():
    user_id = request.args.get("user_id", "")
    now = int(time.time())
    until = access_until.get(user_id, 0)
    return jsonify({
        "active": until > now,
        "until": until,
        "seconds_left": max(0, until - now)
    })

def start_bot():
    if not BOT_TOKEN or telebot is None:
        print("BOT_TOKEN not set. Web app only.")
        return

    bot = telebot.TeleBot(BOT_TOKEN)

    def menu():
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📈 OPEN FOREX AI", web_app=types.WebAppInfo(APP_URL)))
        kb.add(types.InlineKeyboardButton("⭐ 30 минут — 100 Stars", callback_data="buy_30"))
        kb.add(types.InlineKeyboardButton("⭐ 24 часа — 300 Stars", callback_data="buy_24"))
        return kb

    @bot.message_handler(commands=["start"])
    def start(message):
        bot.send_message(
            message.chat.id,
            "📈 Ancient Forex AI\n\n🆓 10 минут бесплатно\n⭐ 30 минут — 100 Stars\n⭐ 24 часа — 300 Stars",
            reply_markup=menu()
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["buy_30", "buy_24"])
    def buy(call):
        if call.data == "buy_30":
            title = "Forex AI — 30 минут"
            payload = "forex_30"
            amount = 100
        else:
            title = "Forex AI — 24 часа"
            payload = "forex_24"
            amount = 300

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=title,
            description="Доступ к учебной Forex-платформе. Без реальных денег, без вывода средств.",
            invoice_payload=payload,
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label=title, amount=amount)]
        )

    @bot.pre_checkout_query_handler(func=lambda q: True)
    def checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @bot.message_handler(content_types=["successful_payment"])
    def paid(message):
        user_id = str(message.from_user.id)
        now = int(time.time())
        current = max(access_until.get(user_id, 0), now)

        payload = message.successful_payment.invoice_payload
        if payload == "forex_30":
            access_until[user_id] = current + 30 * 60
            text = "✅ Оплата получена. Доступ открыт на 30 минут."
        elif payload == "forex_24":
            access_until[user_id] = current + 24 * 60 * 60
            text = "✅ Оплата получена. Доступ открыт на 24 часа."
        else:
            text = "✅ Оплата получена."

        bot.send_message(message.chat.id, text, reply_markup=menu())

    print("Bot polling started")
    bot.infinity_polling(skip_pending=True, timeout=30)

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
