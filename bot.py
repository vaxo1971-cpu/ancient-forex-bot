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

    kb.add(types.InlineKeyboardButton(
        "📈 OPEN FOREX AI",
        web_app=types.WebAppInfo(APP_URL)
    ))

    kb.add(types.InlineKeyboardButton(
        "🆓 FREE / БЕСПЛАТНО / უფასო 10 мин",
        callback_data="trial"
    ))

    kb.add(types.InlineKeyboardButton(
        "⭐ 30 мин — 100 Stars",
        callback_data="buy_30"
    ))

    kb.add(types.InlineKeyboardButton(
        "⭐ 24 часа — 300 Stars",
        callback_data="buy_24"
    ))

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
            """📈 Ancient Forex AI

🇷🇺 Учебная Forex-платформа
🆓 10 минут бесплатно
⭐ 30 минут — 100 Stars
⭐ 24 часа — 300 Stars
Без реальных денег. Без вывода средств.

🇬🇧 Forex Training Platform
🆓 10 minutes free
⭐ 30 minutes — 100 Stars
⭐ 24 hours — 300 Stars
No real money. No withdrawals.

🇬🇪 Forex სასწავლო პლატფორმა
🆓 10 წუთი უფასოდ
⭐ 30 წუთი — 100 Stars
⭐ 24 საათი — 300 Stars
რეალური ფულის გარეშე. თანხის გატანის გარეშე.""",
            reply_markup=menu()
        )

    @bot.callback_query_handler(func=lambda c: c.data in ["trial", "buy_30", "buy_24"])
    def actions(call):
        user = str(call.from_user.id)
        now = int(time.time())

        if call.data == "trial":
            if user in free_used:
                bot.answer_callback_query(
                    call.id,
                    "Пробный период уже использован / Trial already used"
                )
                return

            free_used.add(user)
            access_until[user] = now + 10 * 60

            bot.answer_callback_query(
                call.id,
                "Доступ открыт на 10 минут"
            )

            bot.send_message(
                call.message.chat.id,
                """✅ Доступ открыт на 10 минут.

🇬🇧 Access is open for 10 minutes.
🇬🇪 წვდომა გახსნილია 10 წუთით.""",
                reply_markup=menu()
            )

        elif call.data == "buy_30":
            access_until[user] = now + 30 * 60

            bot.answer_callback_query(
                call.id,
                "Доступ открыт на 30 минут"
            )

            bot.send_message(
                call.message.chat.id,
                """✅ Доступ открыт на 30 минут.

🇬🇧 Access is open for 30 minutes.
🇬🇪 წვდომა გახსნილია 30 წუთით.

⭐ Оплата Telegram Stars будет подключена следующим шагом.""",
                reply_markup=menu()
            )

        elif call.data == "buy_24":
            access_until[user] = now + 24 * 60 * 60

            bot.answer_callback_query(
                call.id,
                "Доступ открыт на 24 часа"
            )

            bot.send_message(
                call.message.chat.id,
                """✅ Доступ открыт на 24 часа.

🇬🇧 Access is open for 24 hours.
🇬🇪 წვდომა გახსნილია 24 საათით.

⭐ Оплата Telegram Stars будет подключена следующим шагом.""",
                reply_markup=menu()
            )

    print("Bot polling started")

    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print("Bot error:", e)


if BOT_TOKEN and telebot is not None:
    threading.Thread(target=start_bot, daemon=True).start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
