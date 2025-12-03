import os
import asyncio
import sqlite3
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ========= НАСТРОЙКИ =========

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

DB_PATH = "crypto_planner.db"
DEFAULT_LANG = "es"  # язык по умолчанию

# ========= БОЛЬШИЕ ПРИВЕТСТВИЯ =========

WELCOME_EXT_ES = """
👋 ¡Bienvenido a Crypto Planner!

Este bot te ayuda a entender el mercado cripto en segundos:

📊 Informe diario (09:00)
₿ BTC y Ξ ETH — precio y riesgo
🔥 Top 5 del mercado
📰 Noticias importantes
⚠️ Riesgos del día
🧠 Índice Miedo/Avaricia
🔔 Alertas de precio (pronto)

Todo en un solo lugar, claro y fácil.
Usa el menú de abajo 👇
"""

WELCOME_EXT_EN = """
👋 Welcome to Crypto Planner!

This bot helps you understand the crypto market in seconds:

📊 Daily report (09:00)
₿ BTC & Ξ ETH — price & risk
🔥 Top 5 of the market
📰 Important news
⚠️ Risks of the day
🧠 Fear & Greed Index
🔔 Price alerts (soon)

Everything in one place, clear and easy.
Use the menu below 👇
"""

# ========= ТЕКСТЫ ДЛЯ МЕНЮ И КНОПОК =========

TEXTS = {
    "en": {
        "choose_language_title": "🌐 Choose language / Elige idioma:",
        "lang_button_es": "🇪🇸 Spanish",
        "lang_button_en": "🇬🇧 English",
        "language_saved": "✅ Language saved: English.",

        "welcome": "👋 Welcome to Crypto Planner!",
        "main_menu_title": "📋 Main menu:",

        "btn_today_report": "📊 Today's report",
        "btn_btc": "₿ Bitcoin (BTC)",
        "btn_eth": "Ξ Ethereum (ETH)",
        "btn_top5": "🔥 Top 5 of the market",
        "btn_news": "📰 Crypto news",
        "btn_risks": "⚠️ Risks of the day",
        "btn_fear_greed": "🧠 Fear & Greed index",
        "btn_alerts": "🔔 Price alerts",
        "btn_settings": "⚙️ Language / Settings",

        "unknown_command": "I don’t understand this yet. Use the menu buttons.",

        "coin_header": "{name} ({symbol})",
        "coin_price_line": "💰 Price: *{price:.2f} EUR* ({change:+.2f}% / 24h)",
        "coin_rank_line": "🏅 Market cap rank: #{rank}",
        "coin_price_text": "📉 *Current price*\n\n{coin_info}\n\n_Data from CoinGecko (EUR)._",

        "coin_risk_text": (
            "⚖️ *Risk / Volatility*\n\n"
            "24h change: *{change:+.2f}%*.\n"
            "{comment}"
        ),

        "coin_inline_price": "📉 Current price",
        "coin_inline_chart": "📈 Chart (soon)",
        "coin_inline_risk": "⚖️ Risk",
        "coin_inline_alert": "🔔 Create alert (soon)",

        "today_report_title": "📊 *Daily crypto report*",
        "today_report_header": "Date: {date}\nTime: {time}",
        "today_report_section_btc_eth": "₿ BTC & Ξ ETH:",
        "today_report_section_top5": "🔥 Top 5 by market cap:",
        "today_report_footer": "_Data from CoinGecko + Fear & Greed index._",

        "top5_line": "{rank}. {name} ({symbol}) — *{price:.2f} EUR* ({change:+.2f}%)",

        "news_stub": (
            "📰 *Crypto news*\n\n"
            "News integration will be added later."
        ),

        "fear_greed_title": "🧠 *Fear & Greed index*",
        "fear_greed_line": "Index: *{value}* — *{classification}*",
        "fear_greed_updated": "Updated: {time}",

        "risks_title": "⚠️ *Risks of the day*",
        "risks_text": (
            "Based on volatility and market sentiment:\n\n{comment}"
        ),

        "broadcast_title": "📢 *Daily Crypto Report*",
        "broadcast_intro": "Here is your daily crypto overview:",

        "settings_text": "⚙️ Use /start to change language.",
        "api_error": "⚠️ API error, try again later.",
    },

    "es": {
        "choose_language_title": "🌐 Choose language / Elige idioma:",
        "lang_button_es": "🇪🇸 Español",
        "lang_button_en": "🇬🇧 Inglés",
        "language_saved": "✅ Idioma guardado: Español.",

        "welcome": "👋 ¡Bienvenido a Crypto Planner!",
        "main_menu_title": "📋 Menú principal:",

        "btn_today_report": "📊 Informe de hoy",
        "btn_btc": "₿ Bitcoin (BTC)",
        "btn_eth": "Ξ Ethereum (ETH)",
        "btn_top5": "🔥 Top 5 del mercado",
        "btn_news": "📰 Noticias cripto",
        "btn_risks": "⚠️ Riesgos del día",
        "btn_fear_greed": "🧠 Índice miedo/avaricia",
        "btn_alerts": "🔔 Alertas de precio",
        "btn_settings": "⚙️ Idioma / Configuración",

        "unknown_command": "No entiendo este mensaje. Usa los botones del menú.",

        "coin_header": "{name} ({symbol})",
        "coin_price_line": "💰 Precio: *{price:.2f} EUR* ({change:+.2f}% / 24h)",
        "coin_rank_line": "🏅 Puesto por capitalización: #{rank}",
        "coin_price_text": "📉 *Precio actual*\n\n{coin_info}\n\n_Datos de CoinGecko (EUR)._",

        "coin_risk_text": (
            "⚖️ *Riesgo / Volatilidad*\n\n"
            "Cambio 24h: *{change:+.2f}%*.\n"
            "{comment}"
        ),

        "coin_inline_price": "📉 Precio actual",
        "coin_inline_chart": "📈 Gráfico (pronto)",
        "coin_inline_risk": "⚖️ Riesgo",
        "coin_inline_alert": "🔔 Crear alerta (pronto)",

        "today_report_title": "📊 *Informe cripto diario*",
        "today_report_header": "Fecha: {date}\nHora: {time}",
        "today_report_section_btc_eth": "₿ BTC y Ξ ETH:",
        "today_report_section_top5": "🔥 Top 5 por capitalización:",
        "today_report_footer": "_Datos de CoinGecko + índice Miedo/Avaricia._",

        "top5_line": "{rank}. {name} ({symbol}) — *{price:.2f} EUR* ({change:+.2f}%)",

        "news_stub": (
            "📰 *Noticias cripto*\n\n"
            "La integración de noticias se añadirá más adelante."
        ),

        "fear_greed_title": "🧠 *Índice miedo/avaricia*",
        "fear_greed_line": "Índice: *{value}* — *{classification}*",
        "fear_greed_updated": "Actualizado: {time}",

        "risks_title": "⚠️ *Riesgos del día*",
        "risks_text": (
            "Basado en volatilidad y sentimiento del mercado:\n\n{comment}"
        ),

        "broadcast_title": "📢 *Informe Cripto Diario*",
        "broadcast_intro": "Aquí tienes tu resumen cripto automático del día:",

        "settings_text": "⚙️ Usa /start para cambiar el idioma.",
        "api_error": "⚠️ Error de API, inténtalo más tarde.",
    }
}
# ========= БАЗА ДАННЫХ =========

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            lang TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def set_user_lang(chat_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (chat_id, lang)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET lang = excluded.lang
        """,
        (chat_id, lang),
    )
    conn.commit()
    conn.close()


def get_user_lang(chat_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]
    return DEFAULT_LANG


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, lang FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows


# ========= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =========

def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["es"])[key]


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=TEXTS["es"]["lang_button_es"], callback_data="lang_es"),
                InlineKeyboardButton(text=TEXTS["en"]["lang_button_en"], callback_data="lang_en"),
            ]
        ]
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    tx = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tx["btn_today_report"])],
            [KeyboardButton(text=tx["btn_btc"]), KeyboardButton(text=tx["btn_eth"])],
            [KeyboardButton(text=tx["btn_top5"])],
            [KeyboardButton(text=tx["btn_news"]), KeyboardButton(text=tx["btn_risks"])],
            [KeyboardButton(text=tx["btn_fear_greed"]), KeyboardButton(text=tx["btn_alerts"])],
            [KeyboardButton(text=tx["btn_settings"])],
        ],
        resize_keyboard=True,
    )


def coin_inline_keyboard(lang: str, coin: str) -> InlineKeyboardMarkup:
    tx = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tx["coin_inline_price"], callback_data=f"coin_{coin}_price")],
            [InlineKeyboardButton(text=tx["coin_inline_risk"], callback_data=f"coin_{coin}_risk")],
            [InlineKeyboardButton(text=tx["coin_inline_chart"], callback_data=f"coin_{coin}_chart")],
            [InlineKeyboardButton(text=tx["coin_inline_alert"], callback_data=f"coin_{coin}_alert")],
        ]
    )


# ========= API =========

COINGECKO_SIMPLE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1&format=json&date_format=world"


async def fetch_json(url: str, params: dict | None = None):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, timeout=20) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except Exception:
        return None


async def get_btc_eth_prices():
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "eur",
        "include_24hr_change": "true",
    }
    return await fetch_json(COINGECKO_SIMPLE_URL, params=params)


async def get_top5():
    params = {
        "vs_currency": "eur",
        "order": "market_cap_desc",
        "per_page": 5,
        "page": 1,
        "price_change_percentage": "24h",
    }
    return await fetch_json(COINGECKO_MARKETS_URL, params=params)


async def get_fear_greed():
    data = await fetch_json(FEAR_GREED_URL)
    if not data or "data" not in data:
        return None

    item = data["data"][0]
    return {
        "value": int(item["value"]),
        "classification": item["value_classification"],
        "time": item["timestamp"],
    }


# ========= ФОРМИРОВАНИЕ ТЕКСТОВ =========

def format_coin_block(lang: str, name: str, symbol: str, price: float, change: float, rank: int):
    tx = TEXTS[lang]
    header = tx["coin_header"].format(name=name, symbol=symbol)
    price_line = tx["coin_price_line"].format(price=price, change=change)
    rank_line = tx["coin_rank_line"].format(rank=rank)
    return f"{header}\n{price_line}\n{rank_line}"


async def build_today_report(lang: str):
    prices = await get_btc_eth_prices()
    top5 = await get_top5()
    fng = await get_fear_greed()

    if not prices or not top5:
        return None

    now = datetime.utcnow()
    tx = TEXTS[lang]

    header = (
        tx["today_report_title"]
        + "\n\n"
        + tx["today_report_header"].format(
            date=now.strftime("%d.%m.%Y"),
            time=now.strftime("%H:%M UTC")
        )
    )

    # BTC / ETH
    btc = prices.get("bitcoin")
    eth = prices.get("ethereum")

    lines_btc_eth = []

    if btc:
        lines_btc_eth.append(
            format_coin_block(lang, "Bitcoin", "BTC", btc["eur"], btc["eur_24h_change"], 1)
        )
    if eth:
        lines_btc_eth.append(
            format_coin_block(lang, "Ethereum", "ETH", eth["eur"], eth["eur_24h_change"], 2)
        )

    block_btc_eth = tx["today_report_section_btc_eth"] + "\n\n" + "\n\n".join(lines_btc_eth)

    # Top 5
    top_lines = []
    for idx, c in enumerate(top5, start=1):
        top_lines.append(
            tx["top5_line"].format(
                rank=idx,
                name=c["name"],
                symbol=c["symbol"].upper(),
                price=c["current_price"],
                change=c["price_change_percentage_24h"] or 0.0,
            )
        )
    block_top5 = tx["today_report_section_top5"] + "\n\n" + "\n".join(top_lines)

    # Fear & Greed
    if fng:
        fng_block = (
            tx["fear_greed_title"]
            + "\n"
            + tx["fear_greed_line"].format(
                value=fng["value"], classification=fng["classification"]
            )
            + "\n"
            + tx["fear_greed_updated"].format(time=fng["time"])
        )
    else:
        fng_block = ""

    parts = [header, block_btc_eth, block_top5]
    if fng_block:
        parts.append(fng_block)
    parts.append(tx["today_report_footer"])

    return "\n\n".join(parts)


async def build_coin_message(lang: str, coin: str, mode: str):
    prices = await get_btc_eth_prices()
    if not prices:
        return None

    if coin == "btc":
        d = prices.get("bitcoin")
        name, symbol, rank = "Bitcoin", "BTC", 1
    else:
        d = prices.get("ethereum")
        name, symbol, rank = "Ethereum", "ETH", 2

    if not d:
        return None

    price = d["eur"]
    change = d["eur_24h_change"]

    tx = TEXTS[lang]

    if mode == "price":
        block = format_coin_block(lang, name, symbol, price, change, rank)
        return tx["coin_price_text"].format(coin_info=block)

    if mode == "risk":
        if abs(change) < 2:
            comment = "Low volatility." if lang == "en" else "Volatilidad baja."
        elif abs(change) < 5:
            comment = "Moderate volatility." if lang == "en" else "Volatilidad moderada."
        else:
            comment = "High volatility — be careful." if lang == "en" else "Alta volatilidad — cuidado."
        return tx["coin_risk_text"].format(change=change, comment=comment)

    return None
# ========= ОБРАБОТЧИКИ =========

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        TEXTS["es"]["choose_language_title"],
        reply_markup=language_keyboard()
    )


@dp.callback_query(F.data.startswith("lang_"))
async def callback_set_language(callback: CallbackQuery):
    chat_id = callback.from_user.id
    lang = callback.data.split("_", maxsplit=1)[1]

    if lang not in TEXTS:
        lang = DEFAULT_LANG

    # сохраняем язык
    set_user_lang(chat_id, lang)

    # закрываем "часики"
    await callback.answer()

    # сообщение "язык сохранён"
    await callback.message.edit_text(
        t(lang, "language_saved"),
        parse_mode="Markdown"
    )

    # отправляем информативное приветствие
    if lang == "es":
        await callback.message.answer(WELCOME_EXT_ES)
    else:
        await callback.message.answer(WELCOME_EXT_EN)

    # отправляем меню
    await callback.message.answer(
        t(lang, "main_menu_title"),
        reply_markup=main_menu_keyboard(lang)
    )


# ========= ГЛАВНОЕ МЕНЮ =========

@dp.message(F.text)
async def handle_text(message: Message):
    chat_id = message.from_user.id
    lang = get_user_lang(chat_id)
    tx = TEXTS[lang]
    txt = message.text.strip()

    # 📊 Informe de hoy
    if txt == tx["btn_today_report"]:
        report = await build_today_report(lang)
        if not report:
            await message.answer(tx["api_error"])
            return
        await message.answer(report, parse_mode="Markdown")
        return

    # BTC
    if txt == tx["btn_btc"]:
        await message.answer(
            "₿ Bitcoin (BTC)",
            reply_markup=coin_inline_keyboard(lang, "btc")
        )
        return

    # ETH
    if txt == tx["btn_eth"]:
        await message.answer(
            "Ξ Ethereum (ETH)",
            reply_markup=coin_inline_keyboard(lang, "eth")
        )
        return

    # 🔥 Top 5
    if txt == tx["btn_top5"]:
        data = await get_top5()
        if not data:
            await message.answer(tx["api_error"])
            return

        lines = []
        for idx, c in enumerate(data, start=1):
            lines.append(
                tx["top5_line"].format(
                    rank=idx,
                    name=c["name"],
                    symbol=c["symbol"].upper(),
                    price=c["current_price"],
                    change=c["price_change_percentage_24h"] or 0.0,
                )
            )

        await message.answer(
            tx["today_report_section_top5"] + "\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )
        return

    # 📰 Noticias
    if txt == tx["btn_news"]:
        await message.answer(tx["news_stub"], parse_mode="Markdown")
        return

    # 🧠 Índice miedo/avaricia
    if txt == tx["btn_fear_greed"]:
        fg = await get_fear_greed()
        if not fg:
            await message.answer(tx["api_error"])
            return

        msg = (
            tx["fear_greed_title"]
            + "\n"
            + tx["fear_greed_line"].format(
                value=fg["value"], classification=fg["classification"]
            )
            + "\n"
            + tx["fear_greed_updated"].format(time=fg["time"])
        )
        await message.answer(msg, parse_mode="Markdown")
        return

    # ⚠️ Riesgos del día
    if txt == tx["btn_risks"]:
        fg = await get_fear_greed()
        if fg:
            v = fg["value"]
            if v <= 20:
                comment = "Miedo extremo: buenas zonas para acumular." if lang == "es" else "Extreme fear: good accumulation zones."
            elif v <= 45:
                comment = "Sentimiento débil pero estable." if lang == "es" else "Weak but stable sentiment."
            elif v <= 70:
                comment = "Avaricia: cuidado con el FOMO." if lang == "es" else "Greed: beware of FOMO."
            else:
                comment = "Avaricia extrema: riesgo de corrección." if lang == "es" else "Extreme greed: correction risk."
        else:
            comment = "Datos no disponibles." if lang == "es" else "Data unavailable."

        text = tx["risks_title"] + "\n\n" + tx["risks_text"].format(comment=comment)
        await message.answer(text, parse_mode="Markdown")
        return

    # 🔔 Alertas (пока заглушка)
    if txt == tx["btn_alerts"]:
        if lang == "es":
            await message.answer("🔔 Las alertas estarán disponibles más adelante.")
        else:
            await message.answer("🔔 Alerts will be available soon.")
        return

    # ⚙️ Configuración
    if txt == tx["btn_settings"]:
        await message.answer(tx["settings_text"])
        return

    # неизвестная команда
    await message.answer(tx["unknown_command"])


# ========= INLINE BTC / ETH =========

@dp.callback_query(F.data.startswith("coin_"))
async def handle_coin(callback: CallbackQuery):
    chat_id = callback.from_user.id
    lang = get_user_lang(chat_id)

    _, coin, action = callback.data.split("_", maxsplit=2)

    await callback.answer()

    if action == "price":
        txt = await build_coin_message(lang, coin, "price")
        if not txt:
            await callback.message.answer(TEXTS[lang]["api_error"])
            return
        await callback.message.answer(txt, parse_mode="Markdown")
        return

    if action == "risk":
        txt = await build_coin_message(lang, coin, "risk")
        if not txt:
            await callback.message.answer(TEXTS[lang]["api_error"])
            return
        await callback.message.answer(txt, parse_mode="Markdown")
        return

    if action == "chart":
        await callback.message.answer(
            TEXTS[lang]["coin_inline_chart"]
        )
        return

    if action == "alert":
        await callback.message.answer(
            TEXTS[lang]["coin_inline_alert"]
        )
        return


# ========= РАССЫЛКА (09:00) =========

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")


async def broadcast_daily_report():
    users = get_all_users()
    if not users:
        return

    for chat_id, lang in users:
        try:
            report = await build_today_report(lang)
            if not report:
                continue

            text_full = (
                TEXTS[lang]["broadcast_title"]
                + "\n\n"
                + TEXTS[lang]["broadcast_intro"]
                + "\n\n"
                + report
            )

            await bot.send_message(chat_id, text_full, parse_mode="Markdown")

        except TelegramForbiddenError:
            # пользователь заблокировал бота
            continue
        except TelegramBadRequest:
            continue
        except Exception:
            continue


# ========= ЗАПУСК =========

async def main():
    print("🚀 Crypto Planner bot started")

    init_db()

    # ежедневная рассылка
    scheduler.add_job(broadcast_daily_report, "cron", hour=9, minute=0)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
