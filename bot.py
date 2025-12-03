import os
import asyncio
import aiohttp
from datetime import datetime
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI

# ------------------------------
# CONFIG
# ------------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CRYPTO_PANIC_KEY = os.getenv("CRYPTO_PANIC_KEY", "")  # можно пустым

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")

bot = Bot(TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DB_PATH = "crypto_planner.db"
DEFAULT_LANG = "es"
scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

# ------------------------------
# МНОГОЯЗЫЧНЫЕ ТЕКСТЫ
# ------------------------------

TEXTS = {
    "es": {
        "choose_lang": "🌐 Elige idioma:",
        "saved": "🇪🇸 Idioma guardado: Español",
        "welcome_ext": """👋 ¡Bienvenido a Crypto Planner!

📊 Informe diario (09:00, automático)
₿ BTC y Ξ ETH — precio y riesgo
🔥 Top 5 del mercado
📰 Noticias importantes
⚡ Noticias urgentes
🚀 Noticias positivas
📉 Noticias negativas
₿ Noticias Bitcoin
Ξ Noticias Ethereum

Todo claro, simple y útil.
""",
        "menu_title": "📋 Menú principal:",
        "btn_today": "📊 Informe de hoy",
        "btn_btc": "₿ Bitcoin",
        "btn_eth": "Ξ Ethereum",
        "btn_top5": "🔥 Top 5 del mercado",
        "btn_news": "📰 Noticias",
        "btn_risks": "⚠️ Riesgos del día",
        "btn_fng": "🧠 Índice miedo/avaricia",
        "btn_settings": "⚙️ Configuración",
        "btn_alerts": "🔔 Alertas",

        "news_menu": "📰 Noticias — elige categoría:",
        "news_important": "🔥 Importantes",
        "news_breaking": "⚡ Urgentes",
        "news_rising": "🚀 Positivas",
        "news_bearish": "📉 Negativas",
        "news_btc": "₿ Noticias Bitcoin",
        "news_eth": "Ξ Noticias Ethereum",

        "api_error": "⚠️ Error al obtener datos",
        "unknown": "No entiendo este mensaje"
    },

    "en": {
        "choose_lang": "🌐 Choose language:",
        "saved": "🇬🇧 Language saved: English",
        "welcome_ext": """👋 Welcome to Crypto Planner!

📊 Daily report (09:00, automatic)
₿ BTC & Ξ ETH — price & risk
🔥 Top 5 market movers
📰 Important news
⚡ Breaking news
🚀 Bullish news
📉 Bearish news
₿ Bitcoin news
Ξ Ethereum news

Everything clear and useful.
""",
        "menu_title": "📋 Main menu:",
        "btn_today": "📊 Today's report",
        "btn_btc": "₿ Bitcoin",
        "btn_eth": "Ξ Ethereum",
        "btn_top5": "🔥 Top 5 market",
        "btn_news": "📰 News",
        "btn_risks": "⚠️ Risks",
        "btn_fng": "🧠 Fear & Greed",
        "btn_settings": "⚙️ Settings",
        "btn_alerts": "🔔 Alerts",

        "news_menu": "📰 News — choose category:",
        "news_important": "🔥 Important",
        "news_breaking": "⚡ Breaking",
        "news_rising": "🚀 Bullish",
        "news_bearish": "📉 Bearish",
        "news_btc": "₿ Bitcoin news",
        "news_eth": "Ξ Ethereum news",

        "api_error": "⚠️ API error",
        "unknown": "I don't understand"
    },

    "ru": {
        "choose_lang": "🌐 Выберите язык:",
        "saved": "🇷🇺 Язык сохранён: Русский",
        "welcome_ext": """👋 Добро пожаловать в Crypto Planner!

📊 Ежедневный отчёт (09:00)
₿ BTC и Ξ ETH — цена и риск
🔥 Топ-5 монет рынка
📰 Важные новости
⚡ Срочные новости
🚀 Позитивные новости
📉 Негативные новости
₿ Новости по Bitcoin
Ξ Новости по Ethereum

Всё понятно, коротко и полезно.
""",
        "menu_title": "📋 Главное меню:",
        "btn_today": "📊 Отчёт за сегодня",
        "btn_btc": "₿ Биткоин",
        "btn_eth": "Ξ Эфириум",
        "btn_top5": "🔥 Топ-5 рынка",
        "btn_news": "📰 Новости",
        "btn_risks": "⚠️ Риски дня",
        "btn_fng": "🧠 Индекс страха/жадности",
        "btn_settings": "⚙️ Настройки",
        "btn_alerts": "🔔 Оповещения",

        "news_menu": "📰 Новости — выбери категорию:",
        "news_important": "🔥 Важные",
        "news_breaking": "⚡ Срочные",
        "news_rising": "🚀 Позитивные",
        "news_bearish": "📉 Негативные",
        "news_btc": "₿ Новости BTC",
        "news_eth": "Ξ Новости ETH",

        "api_error": "⚠️ Ошибка API",
        "unknown": "Команда не распознана"
    }
}

# ------------------------------
# ПЕРЕВОД ТЕКСТА (OpenAI)
# ------------------------------

async def translate_text(text: str, target_lang: str) -> str:
    """Переводит текст на ES / EN / RU через gpt-4.1-mini."""
    try:
        lang_code = {
            "es": "Spanish",
            "en": "English",
            "ru": "Russian"
        }[target_lang]

        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": f"Translate to {lang_code}. Keep it short."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message["content"]
    except Exception:
        return text  # fallback если API упало

# ------------------------------
# CRYPTOPANIC API
# ------------------------------

async def get_crypto_news(kind: str, limit=5):
    """
    kind: important / breaking / rising / bearish / btc / eth
    """
    base = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": CRYPTO_PANIC_KEY,
        "public": "true",
        "filter": kind,
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(base, params=params) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return data.get("results", [])[:limit]
    except:
        return []
# ------------------------------
# БАЗА ДАННЫХ
# ------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            lang TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def set_lang(chat_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (chat_id, lang)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET lang = excluded.lang
    """, (chat_id, lang))
    conn.commit()
    conn.close()


def get_lang(chat_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else DEFAULT_LANG


# ------------------------------
# КЛАВИАТУРЫ
# ------------------------------

def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="set_lang_es"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        ]
    ])


def main_menu(lang):
    tx = TEXTS[lang]
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text=tx["btn_today"])],
            [KeyboardButton(text=tx["btn_btc"]), KeyboardButton(text=tx["btn_eth"])],
            [KeyboardButton(text=tx["btn_top5"])],
            [KeyboardButton(text=tx["btn_news"])],
            [KeyboardButton(text=tx["btn_risks"]), KeyboardButton(text=tx["btn_fng"])],
            [KeyboardButton(text=tx["btn_alerts"])],
            [KeyboardButton(text=tx["btn_settings"])],
        ]
    )


def news_menu(lang):
    tx = TEXTS[lang]
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text=tx["news_important"])],
            [KeyboardButton(text=tx["news_breaking"])],
            [KeyboardButton(text=tx["news_rising"])],
            [KeyboardButton(text=tx["news_bearish"])],
            [KeyboardButton(text=tx["news_btc"]), KeyboardButton(text=tx["news_eth"])],
            [KeyboardButton(text=tx["menu_title"])],
        ]
    )


# ------------------------------
# BTC / ETH PRICE API
# ------------------------------

async def get_prices():
    url = (
        "https://api.coingecko.com/api/v3/simple/price?"
        "ids=bitcoin,ethereum&vs_currencies=eur&include_24hr_change=true"
    )
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except:
        return None


async def get_top5():
    url = (
        "https://api.coingecko.com/api/v3/coins/markets?"
        "vs_currency=eur&order=market_cap_desc&per_page=5&page=1&price_change_percentage=24h"
    )
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except:
        return None


# ------------------------------
# ФОРМАТИРОВАНИЕ НОВОСТЕЙ
# ------------------------------

def format_news_item(item, lang):
    title = item.get("title", "")
    url = item.get("url", "")
    source = item.get("source", {}).get("title", "")
    time = item.get("published_at", "")

    return f"🔹 *{title}*\n📎 {source}\n🕒 {time}\n🔗 {url}\n"


async def fetch_and_translate_news(kind: str, lang: str, limit=5):
    """Получает новости CryptoPanic → переводит → возвращает текст."""
    news = await get_crypto_news(kind, limit)
    if not news:
        return "⚠️ No news available" if lang == "en" else \
               "⚠️ Noticias no disponibles" if lang == "es" else \
               "⚠️ Новости недоступны"

    result = ""
    for item in news:
        text_raw = format_news_item(item, lang)

        # перевод заголовка
        translated_title = await translate_text(item.get("title", ""), lang)
        translated_summary = await translate_text(item.get("domain", ""), lang)

        result += (
            f"🔸 *{translated_title}*\n"
            f"{item.get('url', '')}\n\n"
        )

    return result


# ------------------------------
# ВЫБОР ЯЗЫКА
# ------------------------------

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        TEXTS["es"]["choose_lang"], 
        reply_markup=lang_keyboard()
    )


@dp.callback_query(F.data.startswith("set_lang_"))
async def choose_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[2]
    chat_id = callback.from_user.id

    set_lang(chat_id, lang)

    tx = TEXTS[lang]

    await callback.message.edit_text(tx["saved"])
    await callback.message.answer(tx["welcome_ext"])
    await callback.message.answer(tx["menu_title"], reply_markup=main_menu(lang))


# ------------------------------
# ГЛАВНОЕ МЕНЮ — ОБРАБОТЧИК
# ------------------------------

@dp.message(F.text)
async def main_handler(message: Message):
    chat_id = message.from_user.id
    lang = get_lang(chat_id)
    tx = TEXTS[lang]
    text = message.text

    # ------- ОТЧЁТ О СЕГОДНЯШНЕМ ДНЕ -------
    if text == tx["btn_today"]:
        report = await build_daily_report(lang)
        await message.answer(report, parse_mode="Markdown")
        return

    # ------- BTC -------
    if text == tx["btn_btc"]:
        data = await get_prices()
        if not data:
            await message.answer(tx["api_error"])
            return

        btc = data["bitcoin"]
        price = btc["eur"]
        change = btc["eur_24h_change"]

        msg = f"""₿ *Bitcoin*
💰 {price:.2f} EUR
📈 24h: {change:+.2f}%
"""
        await message.answer(msg, parse_mode="Markdown")
        return

    # ------- ETH -------
    if text == tx["btn_eth"]:
        data = await get_prices()
        if not data:
            await message.answer(tx["api_error"])
            return

        eth = data["ethereum"]
        price = eth["eur"]
        change = eth["eur_24h_change"]

        msg = f"""Ξ *Ethereum*
💰 {price:.2f} EUR
📈 24h: {change:+.2f}%
"""
        await message.answer(msg, parse_mode="Markdown")
        return

    # ------- TOP 5 -------
    if text == tx["btn_top5"]:
        data = await get_top5()
        if not data:
            await message.answer(tx["api_error"])
            return

        msg = "🔥 *Top 5*\n\n"
        for c in data:
            msg += f"{c['market_cap_rank']}. {c['name']} — {c['current_price']} EUR ({c['price_change_percentage_24h']:+.2f}%)\n"

        await message.answer(msg, parse_mode="Markdown")
        return

    # ------- НОВОСТИ -------
    if text == tx["btn_news"]:
        await message.answer(tx["news_menu"], reply_markup=news_menu(lang))
        return

    # ------- КАТЕГОРИИ НОВОСТЕЙ -------
    if text == tx["news_important"]:
        news = await fetch_and_translate_news("important", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    if text == tx["news_breaking"]:
        news = await fetch_and_translate_news("breaking", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    if text == tx["news_rising"]:
        news = await fetch_and_translate_news("rising", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    if text == tx["news_bearish"]:
        news = await fetch_and_translate_news("bearish", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    if text == tx["news_btc"]:
        news = await fetch_and_translate_news("btc", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    if text == tx["news_eth"]:
        news = await fetch_and_translate_news("eth", lang)
        await message.answer(news, parse_mode="Markdown")
        return

    # ------- РИСКИ ДНЯ -------
    if text == tx["btn_risks"]:
        msg = "⚠️ Coming soon"
    # ------- FNG -------
    if text == tx["btn_fng"]:
        msg = "🧠 Coming soon"
    # ------- SETTINGS -------
    if text == tx["btn_settings"]:
        msg = tx["choose_lang"]

    # fallback
    else:
        msg = tx["unknown"]

    await message.answer(msg)
# ------------------------------
# FEAR & GREED INDEX
# ------------------------------

async def get_fng():
    url = "https://api.alternative.me/fng/?limit=1&format=json"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                item = data["data"][0]
                return {
                    "value": item["value"],
                    "classification": item["value_classification"],
                    "time": item["timestamp"]
                }
    except:
        return None


# ------------------------------
# ДНЕВНОЙ ОТЧЁТ
# ------------------------------

async def build_daily_report(lang: str):
    tx = TEXTS[lang]

    # --- цены ---
    prices = await get_prices()
    top5 = await get_top5()
    fng = await get_fng()

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    msg = f"📊 *Daily Crypto Report*\n{now}\n\n"

    if prices:
        btc = prices["bitcoin"]
        eth = prices["ethereum"]

        msg += (
            f"₿ *Bitcoin*\n"
            f"💰 {btc['eur']:.2f} EUR\n"
            f"📈 {btc['eur_24h_change']:+.2f}%\n\n"
            f"Ξ *Ethereum*\n"
            f"💰 {eth['eur']:.2f} EUR\n"
            f"📈 {eth['eur_24h_change']:+.2f}%\n\n"
        )

    # --- топ 5 ---
    if top5:
        msg += "🔥 *Top 5*\n"
        for c in top5:
            msg += f"{c['market_cap_rank']}. {c['name']} — {c['current_price']} EUR ({c['price_change_percentage_24h']:+.2f}%)\n"
        msg += "\n"

    # --- FNG ---
    if fng:
        msg += (
            "🧠 *Fear & Greed*\n"
            f"Index: {fng['value']}\n"
            f"{fng['classification']}\n"
            f"Updated: {fng['time']}\n\n"
        )

    # --- добавляем новости ---
    msg += "📰 *Top 3 News*\n"
    news = await get_crypto_news("important", limit=3)

    if not news:
        msg += "No news\n"
    else:
        for item in news:
            title = await translate_text(item["title"], lang)
            url = item["url"]
            msg += f"• *{title}*\n{url}\n\n"

    return msg


# ------------------------------
# РАССЫЛКА 09:00
# ------------------------------

async def broadcast_daily():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, lang FROM users")
    users = cur.fetchall()
    conn.close()

    for chat_id, lang in users:
        try:
            report = await build_daily_report(lang)
            await bot.send_message(chat_id, report, parse_mode="Markdown")
        except:
            continue


scheduler.add_job(broadcast_daily, "cron", hour=9, minute=0)


# ------------------------------
# ЗАПУСК БОТА
# ------------------------------

async def main():
    print("🚀 Crypto Planner v2.0 started")
    init_db()
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
