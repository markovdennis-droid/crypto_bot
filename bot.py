import os
import asyncio
import logging
import sqlite3
from contextlib import closing
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties  # 👈 НОВЫЙ ИМПОРТ

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from dotenv import load_dotenv
import pytz

# ------------------ НАСТРОЙКИ И ЛОГИ ------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()  # грузим .env локально (на Render переменные зададим в настройках)

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")

# Часовой пояс Испании
TZ = pytz.timezone("Europe/Madrid")

DB_PATH = "crypto_bot.db"

# 👇 ВАЖНО: вот тут мы исправили parse_mode под новую версию aiogram
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode="Markdown"),
)
dp = Dispatcher()

scheduler = AsyncIOScheduler(timezone=TZ)

# ------------------ БД: ПОДПИСЧИКИ ------------------


def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY
            );
            """
        )
        conn.commit()


def add_subscriber(chat_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?);",
            (chat_id,),
        )
        conn.commit()


def get_all_subscribers():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT chat_id FROM subscribers;")
        rows = cur.fetchall()
    return [row[0] for row in rows]


# ------------------ КЛАВИАТУРА ------------------

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Informe de hoy")],
        [
            KeyboardButton(text="₿ Bitcoin (BTC)"),
            KeyboardButton(text="Ξ Ethereum (ETH)"),
        ],
        [KeyboardButton(text="🌞 Solana (SOL)")],
        [
            KeyboardButton(text="🧠 Sentimiento del mercado"),
            KeyboardButton(text="📰 Noticias cripto"),
        ],
        [KeyboardButton(text="🔔 Crear alerta de precio")],
    ],
    resize_keyboard=True,
)

# Простое состояние для создания алертов (MVP)
user_alert_state = {}  # {user_id: {"step": "...", "coin": "BTC"}}


# ------------------ ГЕНЕРАТОРЫ ТЕКСТОВ (ПОКА ЗАГЛУШКИ) ------------------


def generate_daily_report() -> str:
    # TODO: сюда потом прикрутим реальные данные (CoinGecko и т.д.)
    today_str = datetime.now(TZ).strftime("%d.%m.%Y")
    return (
        f"📊 *Informe cripto de hoy* — {today_str}\n\n"
        "• Mercado general: ligero movimiento lateral.\n"
        "• BTC: consolidando cerca de soportes clave.\n"
        "• ETH: muestra algo más de fuerza que BTC.\n\n"
        "⚠️ Esto no es consejo financiero, solo información."
    )


def generate_coin_overview(coin: str) -> str:
    coin = coin.upper()
    if coin == "BTC":
        name = "Bitcoin"
        symbol = "₿"
    elif coin == "ETH":
        name = "Ethereum"
        symbol = "Ξ"
    elif coin == "SOL":
        name = "Solana"
        symbol = "🌞"
    else:
        name = coin
        symbol = ""

    return (
        f"{symbol} *{name}*\n\n"
        "• Tendencia: consolidación a corto plazo.\n"
        "• Riesgo: medio.\n"
        "• Comentario: día más adecuado para observar que para operar impulsivamente."
    )


def generate_sentiment() -> str:
    # TODO: потом прикрутим реальный индекс miedo/avaricia
    return (
        "🧠 *Sentimiento del mercado*\n\n"
        "• Índice Miedo/Avaricia: 62 (avaricia moderada).\n"
        "• Interpretación: el mercado está optimista, "
        "pero aumenta el riesgo de correcciones rápidas."
    )


def generate_news() -> str:
    # TODO: сюда прикручиваем реальные новости
    return (
        "📰 *Noticias cripto principales (últimas 24h)*\n\n"
        "1) Reguladores europeos debaten nuevas normas para exchanges.\n"
        "2) Un gran fondo institucional aumenta exposición a BTC.\n"
        "3) Crece el volumen en DeFi tras últimas subidas del mercado.\n\n"
        "Resumen: mucha atención a regulaciones y movimientos de grandes jugadores."
    )


# ------------------ ОБРАБОТЧИКИ СООБЩЕНИЙ ------------------


@dp.message(CommandStart())
async def cmd_start(message: Message):
    add_subscriber(message.chat.id)

    text = (
        "👋 Bienvenido al bot de análisis cripto diario.\n\n"
        "Cada mañana recibirás un resumen corto del mercado cripto.\n"
        "También puedes consultar BTC, ETH, SOL, sentimiento y noticias cuando quieras.\n\n"
        "Elige una opción del menú de abajo:"
    )
    await message.answer(text, reply_markup=main_keyboard)


@dp.message(F.text == "📊 Informe de hoy")
async def handle_hoy(message: Message):
    add_subscriber(message.chat.id)
    report = generate_daily_report()
    await message.answer(report)


@dp.message(F.text == "₿ Bitcoin (BTC)")
async def handle_btc(message: Message):
    add_subscriber(message.chat.id)
    text = generate_coin_overview("BTC")
    await message.answer(text)


@dp.message(F.text == "Ξ Ethereum (ETH)")
async def handle_eth(message: Message):
    add_subscriber(message.chat.id)
    text = generate_coin_overview("ETH")
    await message.answer(text)


@dp.message(F.text == "🌞 Solana (SOL)")
async def handle_sol(message: Message):
    add_subscriber(message.chat.id)
    text = generate_coin_overview("SOL")
    await message.answer(text)


@dp.message(F.text == "🧠 Sentimiento del mercado")
async def handle_sentimiento(message: Message):
    add_subscriber(message.chat.id)
    text = generate_sentiment()
    await message.answer(text)


@dp.message(F.text == "📰 Noticias cripto")
async def handle_news(message: Message):
    add_subscriber(message.chat.id)
    text = generate_news()
    await message.answer(text)


@dp.message(F.text == "🔔 Crear alerta de precio")
async def handle_create_alert(message: Message):
    add_subscriber(message.chat.id)
    user_alert_state[message.from_user.id] = {"step": "choose_coin"}
    await message.answer(
        "🔔 ¿Para qué moneda quieres crear una alerta?\n\n"
        "Escribe: BTC, ETH o SOL."
    )


@dp.message()
async def handle_free_text(message: Message):
    user_id = message.from_user.id
    state = user_alert_state.get(user_id)

    # Пользователь в процессе создания алерта
    if state:
        # Шаг 1: выбор монеты
        if state["step"] == "choose_coin":
            coin = message.text.strip().upper()
            if coin not in ("BTC", "ETH", "SOL"):
                await message.answer("Por favor, escribe BTC, ETH o SOL.")
                return
            state["coin"] = coin
            state["step"] = "enter_price"
            await message.answer(
                f"Perfecto. Ahora escribe el precio en euros para {coin}.\n"
                "Ejemplo: 41000"
            )
            return

        # Шаг 2: ввод цены
        if state["step"] == "enter_price":
            try:
                price = float(message.text.replace(",", "."))
            except ValueError:
                await message.answer(
                    "No he entendido el número. Intenta de nuevo (solo cifras)."
                )
                return

            coin = state["coin"]
            # TODO: здесь можно сохранить алерт в БД (отдельная таблица alerts)
            # Сейчас просто подтверждаем создание

            user_alert_state.pop(user_id, None)

            await message.answer(
                f"✅ Alerta creada:\n\n"
                f"Te avisaré cuando {coin} llegue a {price:.2f} €.\n"
                "(De momento es demo, sin notificaciones reales.)"
            )
            return

    # Если не в состоянии алерта — отвечаем базово
    await message.answer(
        "No he entendido tu mensaje.\n"
        "Usa el menú de abajo para elegir una opción."
    )


# ------------------ ЕЖЕДНЕВНАЯ РАССЫЛКА ------------------


async def broadcast_daily_report():
    """Отправка ежедневного отчёта всем подписчикам."""
    subscribers = get_all_subscribers()
    if not subscribers:
        logger.info("Нет подписчиков для рассылки.")
        return

    report = generate_daily_report()
    logger.info(f"Рассылаем отчёт {len(subscribers)} подписчикам.")

    for chat_id in subscribers:
        try:
            await bot.send_message(chat_id, report)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение {chat_id}: {e}")


def setup_scheduler():
    # Каждый день в 09:00 по Мадриду
    trigger = CronTrigger(hour=9, minute=0)
    scheduler.add_job(broadcast_daily_report, trigger)
    scheduler.start()
    logger.info("Планировщик ежедневной рассылки запущен.")


# ------------------ MAIN ------------------


async def main():
    init_db()
    setup_scheduler()
    logger.info("Бот запущен. Начинаем polling.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
