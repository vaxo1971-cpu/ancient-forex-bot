import os
import time
from flask import Flask, send_from_directory, jsonify, request, abort

try:
    import telebot
    from telebot import types
except Exception:
    telebot = None
    types = None


APP_URL = "https://ancient-forex-bot.onrender.com"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Flask(__name__)

access_until = {}
free_used = set()

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN and telebot else None


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
        web_app=types.WebAppInfo(APP_URL + "/")
    ))

    kb.add(types.InlineKeyboardButton(
        "🆓 FREE / БЕСПЛАТНО / უფასო 10 мин",
        callback_data="trial"
    ))

    kb.add(types.InlineKeyboardButton(
        "⭐ 30 мин — 100 Stars",
        callback_data="pay_30"
    ))

    kb.add(types.InlineKeyboardButton(
        "⭐ 24 часа — 300 Stars",
        callback_data="pay_24"
    ))

    return kb


if bot:

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


    @bot.callback_query_handler(func=lambda c: c.data == "trial")
    def trial(call):
        user = str(call.from_user.id)
        now = int(time.time())

        if user in free_used:
            bot.answer_callback_query(
                call.id,
                "Пробный период уже использован / Trial already used"
            )
            return

        free_used.add(user)
        access_until[user] = now + 10 * 60

        bot.answer_callback_query(call.id, "Доступ открыт на 10 минут")

        bot.send_message(
            call.message.chat.id,
            """✅ Доступ открыт на 10 минут.

🇬🇧 Access is open for 10 minutes.
🇬🇪 წვდომა გახსნილია 10 წუთით.""",
            reply_markup=menu()
        )


    @bot.callback_query_handler(func=lambda c: c.data in ["pay_30", "pay_24"])
    def pay(call):
        if call.data == "pay_30":
            title = "Ancient Forex AI — 30 minutes"
            description = "Access to Forex training platform for 30 minutes"
            payload = "access_30"
            amount = 100
        else:
            title = "Ancient Forex AI — 24 hours"
            description = "Access to Forex training platform for 24 hours"
            payload = "access_24"
            amount = 300

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=title,
            description=description,
            invoice_payload=payload,
            provider_token="",
            currency="XTR",
            prices=[
                types.LabeledPrice(
                    label=title,
                    amount=amount
                )
            ]
        )

        bot.answer_callback_query(call.id)


    @bot.pre_checkout_query_handler(func=lambda query: True)
    def checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True
        )


    @bot.message_handler(content_types=["successful_payment"])
    def successful_payment(message):
        user = str(message.from_user.id)
        now = int(time.time())
        payload = message.successful_payment.invoice_payload

        if payload == "access_30":
            access_until[user] = now + 30 * 60
            text = """✅ Оплата прошла успешно.
Доступ открыт на 30 минут.

🇬🇧 Payment successful. Access is open for 30 minutes.
🇬🇪 გადახდა წარმატებულია. წვდომა გახსნილია 30 წუთით."""
        elif payload == "access_24":
            access_until[user] = now + 24 * 60 * 60
            text = """✅ Оплата прошла успешно.
Доступ открыт на 24 часа.

🇬🇧 Payment successful. Access is open for 24 hours.
🇬🇪 გადახდა წარმატებულია. წვდომა გახსნილია 24 საათით."""
        else:
            text = "✅ Payment successful."

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=menu()
        )


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if not bot:
        abort(500)

    update = types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200


def setup_webhook():
    if not bot:
        print("BOT_TOKEN missing or telebot not installed")
        return

    webhook_url = f"{APP_URL}/webhook/{BOT_TOKEN}"

    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print("Webhook set:", webhook_url)
    except Exception as e:
        print("Webhook setup error:", e)


setup_webhook()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
