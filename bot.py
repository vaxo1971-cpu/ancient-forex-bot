import os
import time
from flask import Flask, request, jsonify, send_from_directory

import telebot
from telebot import types


APP_URL = os.getenv("APP_URL", "https://ancient-forex-bot.onrender.com").rstrip("/")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_PATH = "/webhook"

app = Flask(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML") if BOT_TOKEN else None

access_until = {}
free_used = set()
stats = {
    "starts": 0,
    "free_trials": 0,
    "payments": 0,
}


GAME_URL = APP_URL


def main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)

    kb.add(types.InlineKeyboardButton("🎮 Играть", web_app=types.WebAppInfo(GAME_URL)))
    kb.add(types.InlineKeyboardButton("🎁 Бесплатный демо-доступ", callback_data="free_demo"))
    kb.add(types.InlineKeyboardButton("⭐ Купить доступ 1 час — 50 Stars", callback_data="buy_1h"))
    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    kb.add(types.InlineKeyboardButton("ℹ️ Информация", callback_data="info"))

    return kb


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


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if not bot:
        return "BOT_TOKEN missing", 500

    json_data = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200


if bot:

    @bot.message_handler(commands=["start"])
    def start(message):
        stats["starts"] += 1

        text = (
            "🏛 <b>Ancient Card Games</b>\n\n"
            "Добро пожаловать!\n\n"
            "🎮 Играй в древние карточные игры.\n"
            "🎁 Можно получить бесплатный демо-доступ.\n"
            "⭐ Полный доступ покупается через Telegram Stars."
        )

        bot.send_message(message.chat.id, text, reply_markup=main_menu())


    @bot.callback_query_handler(func=lambda call: True)
    def callback(call):
        user_id = str(call.from_user.id)
        now = int(time.time())

        if call.data == "free_demo":
            if user_id in free_used:
                bot.answer_callback_query(call.id, "Вы уже использовали бесплатный доступ.")
                bot.send_message(
                    call.message.chat.id,
                    "⚠️ Бесплатный демо-доступ уже использован.\n\n"
                    "Можно купить доступ через Telegram Stars.",
                    reply_markup=main_menu()
                )
                return

            free_used.add(user_id)
            access_until[user_id] = now + 10 * 60
            stats["free_trials"] += 1

            bot.answer_callback_query(call.id, "Демо-доступ активирован на 10 минут.")
            bot.send_message(
                call.message.chat.id,
                "🎁 Демо-доступ активирован на 10 минут.\n\n"
                "Нажмите 🎮 Играть.",
                reply_markup=main_menu()
            )

        elif call.data == "buy_1h":
            prices = [types.LabeledPrice(label="1 час доступа", amount=50)]

            bot.send_invoice(
                chat_id=call.message.chat.id,
                title="Ancient Card Games — 1 час доступа",
                description="Доступ к игре на 1 час",
                invoice_payload="access_1h",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter="access_1h"
            )

        elif call.data == "stats":
            until = access_until.get(user_id, 0)
            seconds_left = max(0, until - now)

            text = (
                "📊 <b>Статистика</b>\n\n"
                f"Запусков бота: {stats['starts']}\n"
                f"Демо-доступов: {stats['free_trials']}\n"
                f"Покупок: {stats['payments']}\n\n"
                f"Ваш доступ активен: {'✅ Да' if seconds_left > 0 else '❌ Нет'}\n"
                f"Осталось секунд: {seconds_left}"
            )

            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, text, reply_markup=main_menu())

        elif call.data == "info":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "ℹ️ Это развлекательная карточная игра.\n\n"
                "Нет азартной игры на реальные деньги.\n"
                "Нет вывода средств.\n"
                "Нет денежных призов.",
                reply_markup=main_menu()
            )


    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


    @bot.message_handler(content_types=["successful_payment"])
    def successful_payment(message):
        user_id = str(message.from_user.id)
        now = int(time.time())

        access_until[user_id] = now + 60 * 60
        stats["payments"] += 1

        bot.send_message(
            message.chat.id,
            "✅ Оплата получена.\n\n"
            "Доступ активирован на 1 час.\n"
            "Нажмите 🎮 Играть.",
            reply_markup=main_menu()
        )


def setup_webhook():
    if not bot:
        print("BOT_TOKEN is missing")
        return

    webhook_url = APP_URL + WEBHOOK_PATH

    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)

    print(f"Webhook set: {webhook_url}")


if __name__ == "__main__":
    setup_webhook()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
