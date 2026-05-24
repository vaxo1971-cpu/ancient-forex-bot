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
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

access_until = {}
free_used = set()


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


def menu():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "📈 OPEN FOREX AI",
            web_app=types.WebAppInfo(APP_URL)
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🆓 10 минут бесплатно",
            callback_data="trial"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⭐ 30 минут — 100 Stars",
            callback_data="buy_30"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⭐ 24 часа — 300 Stars",
            callback_data="buy_24"
        )
    )

    return kb


def start_bot():

    if not BOT_TOKEN:
        print("BOT_TOKEN missing")
        return

    if telebot is None:
        print("telebot not installed")
        return

    bot = telebot.TeleBot(BOT_TOKEN)

    @bot.message_handler(commands=["start"])
    def start(message):

        bot.send_message(
            message.chat.id,
            """
📈 Ancient Forex AI

Учебная Forex-платформа

🆓 10 минут бесплатно
⭐ 30 минут — 100 Stars
⭐ 24 часа — 300 Stars

Без реальных денег.
Без вывода средств.
            """,
            reply_markup=menu()
        )

    @bot.callback_query_handler(
        func=lambda c:
        c.data in ["trial", "buy_30", "buy_24"]
    )
    def actions(call):

        user = str(call.from_user.id)

        if call.data == "trial":

            if user in free_used:

                bot.answer_callback_query(
                    call.id,
                    "Пробный период уже использован"
                )
                return

            free_used.add(user)

            access_until[user] = (
                int(time.time())
               
