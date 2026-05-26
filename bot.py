import os
import time
import json
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request, abort

import telebot
from telebot import types


# ============================================================
# ANCIENT CARD GAMES BOT
# Русский интерфейс + доступ + статистика + Telegram Stars
# Без Forex
# ============================================================

# Сайт игры Ancient Card Games
APP_URL = "https://aquamarine-strudel-14e0ed.netlify.app"

# Render URL именно сервиса бота
RENDER_URL = os.getenv("RENDER_URL", "https://ancient-forex-bot.onrender.com").rstrip("/")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ancient-card-games-secret").strip()

WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

DATA_FILE = Path("bot_data.json")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML") if BOT_TOKEN else None


# ============================================================
# ХРАНИЛИЩЕ
# ============================================================

def default_data():
    return {
        "access_until": {},
        "free_used": [],
        "stats": {
            "starts": 0,
            "free_activations": 0,
            "payments": 0,
            "paid_users": [],
            "last_payments": []
        }
    }


def load_data():
    if not DATA_FILE.exists():
        return default_data()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        base = default_data()
        base.update(data)
        base["stats"].update(data.get("stats", {}))
        return base
    except Exception:
        return default_data()


def save_data():
    try:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(DATA, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("DATA SAVE ERROR:", e)


DATA = load_data()


def get_access_until(user_id):
    return int(DATA["access_until"].get(str(user_id), 0))


def set_access(user_id, seconds):
    user_id = str(user_id)
    now = int(time.time())
    current_until = max(get_access_until(user_id), now)
    DATA["access_until"][user_id] = current_until + int(seconds)
    save_data()


def has_access(user_id):
    return get_access_until(user_id) > int(time.time())


def format_left(seconds):
    seconds = max(0, int(seconds))
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        return f"{days} дн. {hours} ч. {minutes} мин."
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    return f"{minutes} мин."


# ============================================================
# WEB
# ============================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return "OK", 200


@app.route("/api/access")
def api_access():
    user_id = request.args.get("user_id", "").strip()
    now = int(time.time())
    until = get_access_until(user_id)

    return jsonify({
        "active": until > now,
        "until": until,
        "seconds_left": max(0, until - now)
    })


@app.route("/api/stats")
def api_stats():
    now = int(time.time())
    active_users = sum(1 for v in DATA["access_until"].values() if int(v) > now)

    return jsonify({
        "starts": DATA["stats"]["starts"],
        "free_activations": DATA["stats"]["free_activations"],
        "payments": DATA["stats"]["payments"],
        "paid_users": len(DATA["stats"]["paid_users"]),
        "active_users": active_users
    })


# ============================================================
# ТЕКСТЫ И КНОПКИ
# ============================================================

def start_text():
    return (
        "🃏 <b>Ancient Card Games</b>\n\n"
        "🎮 <b>Древние карточные игры</b>\n\n"
        "🃏 Ancient Poker\n"
        "🂡 Emperor's 21\n"
        "🃏 Joker Duel\n\n"
        "🆓 Бесплатно — 5 минут\n"
        "⭐ 1 час — 50 Stars\n"
        "⭐ 24 часа — 150 Stars\n"
        "⭐ 48 часов — 300 Stars\n\n"
        "Только обучение и развлечение.\n"
        "Без реальных денег. Без азартных игр. Без вывода средств."
    )


def main_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)

    kb.add(types.InlineKeyboardButton(
        "🎮 ИГРАТЬ",
        web_app=types.WebAppInfo(APP_URL)
    ))

    kb.add(types.InlineKeyboardButton("🆓 БЕСПЛАТНО 5 МИНУТ", callback_data="free_5"))
    kb.add(types.InlineKeyboardButton("⭐ 1 ЧАС — 50 STARS", callback_data="pay_1h"))
    kb.add(types.InlineKeyboardButton("⭐ 24 ЧАСА — 150 STARS", callback_data="pay_24h"))
    kb.add(types.InlineKeyboardButton("⭐ 48 ЧАСОВ — 300 STARS", callback_data="pay_48h"))
    kb.add(types.InlineKeyboardButton("⏳ МОЙ ДОСТУП", callback_data="my_access"))
    kb.add(types.InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats"))

    return kb


def access_message(user_id):
    now = int(time.time())
    until = get_access_until(user_id)

    if until <= now:
        return (
            "⛔ <b>Доступ не активен.</b>\n\n"
            "Можно включить бесплатный доступ на 5 минут или купить доступ через Telegram Stars."
        )

    return (
        "✅ <b>Доступ активен.</b>\n\n"
        f"⏳ Осталось: <b>{format_left(until - now)}</b>"
    )


def stats_message():
    now = int(time.time())
    active_users = sum(1 for v in DATA["access_until"].values() if int(v) > now)

    return (
        "📊 <b>Статистика Ancient Card Games</b>\n\n"
        f"▶️ Запусков /start: <b>{DATA['stats']['starts']}</b>\n"
        f"🆓 Бесплатных активаций: <b>{DATA['stats']['free_activations']}</b>\n"
        f"⭐ Покупок: <b>{DATA['stats']['payments']}</b>\n"
        f"👤 Оплативших пользователей: <b>{len(DATA['stats']['paid_users'])}</b>\n"
        f"✅ Активных доступов сейчас: <b>{active_users}</b>"
    )


# ============================================================
# TELEGRAM BOT
# ============================================================

if bot:

    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        DATA["stats"]["starts"] += 1
        save_data()
        bot.send_message(message.chat.id, start_text(), reply_markup=main_keyboard())


    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = str(call.from_user.id)

        if call.data == "free_5":
            if user_id in DATA["free_used"]:
                bot.answer_callback_query(call.id, "Бесплатный доступ уже использован.")
                bot.send_message(
                    call.message.chat.id,
                    "⛔ Вы уже использовали бесплатные 5 минут.",
                    reply_markup=main_keyboard()
                )
                return

            DATA["free_used"].append(user_id)
            DATA["stats"]["free_activations"] += 1
            set_access(user_id, 5 * 60)

            bot.answer_callback_query(call.id, "Бесплатный доступ включён.")
            bot.send_message(
                call.message.chat.id,
                "🆓 <b>Бесплатный доступ включён на 5 минут.</b>",
                reply_markup=main_keyboard()
            )

        elif call.data == "my_access":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                access_message(user_id),
                reply_markup=main_keyboard()
            )

        elif call.data == "stats":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                stats_message(),
                reply_markup=main_keyboard()
            )

        elif call.data in ("pay_1h", "pay_24h", "pay_48h"):
            bot.answer_callback_query(call.id)

            if call.data == "pay_1h":
                title = "Ancient Card Games — доступ на 1 час"
                description = "Доступ к Ancient Card Games на 1 час"
                payload = "access_1h"
                amount = 50
            elif call.data == "pay_24h":
                title = "Ancient Card Games — доступ на 24 часа"
                description = "Доступ к Ancient Card Games на 24 часа"
                payload = "access_24h"
                amount = 150
            else:
                title = "Ancient Card Games — доступ на 48 часов"
                description = "Доступ к Ancient Card Games на 48 часов"
                payload = "access_48h"
                amount = 300

            prices = [types.LabeledPrice(label=title, amount=amount)]

            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=title,
                description=description,
                invoice_payload=payload,
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter=payload
            )


    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


    @bot.message_handler(content_types=["successful_payment"])
    def successful_payment(message):
        user_id = str(message.from_user.id)
        payload = message.successful_payment.invoice_payload

        if payload == "access_1h":
            set_access(user_id, 60 * 60)
            text = "✅ Оплата прошла успешно.\n⭐ Доступ включён на 1 час."
        elif payload == "access_24h":
            set_access(user_id, 24 * 60 * 60)
            text = "✅ Оплата прошла успешно.\n⭐ Доступ включён на 24 часа."
        elif payload == "access_48h":
            set_access(user_id, 48 * 60 * 60)
            text = "✅ Оплата прошла успешно.\n⭐ Доступ включён на 48 часов."
        else:
            text = "✅ Оплата прошла успешно."

        DATA["stats"]["payments"] += 1

        if user_id not in DATA["stats"]["paid_users"]:
            DATA["stats"]["paid_users"].append(user_id)

        DATA["stats"]["last_payments"].append({
            "user_id": user_id,
            "payload": payload,
            "time": int(time.time())
        })

        save_data()

        bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


# ============================================================
# WEBHOOK
# ============================================================

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    if not bot:
        abort(500)

    try:
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
    except Exception as e:
        print("WEBHOOK PROCESS ERROR:", e)

    return "OK", 200


_webhook_configured = False

@app.before_request
def configure_webhook_once():
    global _webhook_configured

    if _webhook_configured or not bot:
        return

    try:
        bot.remove_webhook()
        time.sleep(0.5)
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook set:", WEBHOOK_URL)
        _webhook_configured = True
    except Exception as e:
        print("WEBHOOK SET ERROR:", e)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
