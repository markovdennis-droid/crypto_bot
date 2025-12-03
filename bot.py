import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

# ========= НАСТРОЙКИ =========

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ========= ХРАНЕНИЕ ЯЗЫКА ПОЛЬЗОВАТЕЛЯ =========
# Пока просто в памяти. Потом можно перенести в SQLite.
user_lang: dict[int, str] = {}  # user_id -> "es" или "en"

# ========= ТЕКСТЫ =========

TEXTS = {
    "en": {
        "choose_language": "🌐 Choose your language:",
        "lang_button_es": "🇪🇸 Spanish",
        "lang_button_en": "🇬🇧 English",
        "welcome": "👋 Welcome to *Crypto Planner*!\n\n"
                   "I will help you track the crypto market and plan your buys.",
        "main_menu_title": "📋 Main menu:",
        "btn_today_overview": "📊 Today's crypto overview",
        "btn_plan": "📈 DCA / Investment plan",
        "btn_settings": "⚙️ Settings",
        "unknown_command": "I don’t understand this yet. Please use the menu buttons.",
        "today_stub": "📊 Here will be today's crypto overview for the main coins "
                      "(BTC, ETH, etc.) in EUR.\n\n"
                      "We’ll add real data in the next step.",
        "plan_stub": "📈 Here we'll set up your DCA / investment plan.\n\n"
                     "Soon you will be able to choose:\n"
                     "• coin\n• amount\n• period (daily/weekly/monthly).",
        "settings_stub": "⚙️ Settings will be here later.\n"
                         "For now, you can /start again to change language.",
        "language_saved": "✅ Language saved: English.\n\nUse the menu below 👇",
    },
    "es": {
        "choose_language": "🌐 Elige tu idioma:",
        "lang_button_es": "🇪🇸 Español",
        "lang_button_en": "🇬🇧 Inglés",
        "welcome": "👋 ¡Bienvenido a *Crypto Planner*!\n\n"
                   "Te ayudaré a seguir el mercado cripto y planificar tus compras.",
        "main_menu_title": "📋 Menú principal:",
        "btn_today_overview": "📊 Resumen cripto de hoy",
        "btn_plan": "📈 Plan DCA / inversión",
        "btn_settings": "⚙️ Ajustes",
        "unknown_command": "Todavía no entiendo este mensaje. Usa los botones del menú.",
        "today_stub": "📊 Aquí aparecerá el resumen cripto de hoy para las monedas "
                      "principales (BTC, ETH, etc.) en EUR.\n\n"
                      "Añadiremos datos reales en el siguiente paso.",
        "plan_stub": "📈 Aquí configuraremos tu plan DCA / inversión.\n\n"
                     "Pronto podrás elegir:\n"
                     "• moneda\n• cantidad\n• período (diario/semanal/mensual).",
        "settings_stub": "⚙️ Aquí estarán los ajustes más adelante.\n"
                         "Por ahora puedes usar /start otra vez para cambiar el idioma.",
        "language_saved": "✅ Idioma guardado: Español.\n\nUsa el menú de abajo 👇",
    },
}

DEFAULT_LANG = "es"  # если что-то пойдёт не так — считаем, что испанский


def get_lang(user_id: int) -> str:
    return user_lang.get(user_id, DEFAULT_LANG)


def t(user_id: int, key: str) -> str:
    lang = get_lang(user_id)
    return TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]


# ========= КЛАВИАТУРЫ =========

def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=TEXTS["es"]["lang_button_es"],
                    callback_data="lang_es"
                ),
                InlineKeyboardButton(
                    text=TEXTS["en"]["lang_button_en"],
                    callback_data="lang_en"
                )
            ]
        ]
    )


def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    texts = TEXTS[lang]

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["btn_today_overview"])],
            [KeyboardButton(text=texts["btn_plan"])],
            [KeyboardButton(text=texts["btn_settings"])],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# ========= ОБРАБОТЧИКИ =========

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """
    /start — сначала показываем выбор языка.
    """
    # Сбрасываем язык, чтобы при /start можно было выбрать заново
    user_lang.pop(message.from_user.id, None)

    await message.answer(
        "🌐 Choose language / Elige idioma:",
        reply_markup=language_keyboard()
    )


@dp.callback_query(F.data.startswith("lang_"))
async def callback_set_language(callback: CallbackQuery):
    """
    Пользователь нажал на кнопку выбора языка.
    """
    user_id = callback.from_user.id
    lang_code = callback.data.split("_", maxsplit=1)[1]  # "es" или "en"

    if lang_code not in TEXTS:
        lang_code = DEFAULT_LANG

    user_lang[user_id] = lang_code

    # Удаляем клаву и шлём приветствие + меню
    await callback.answer()  # просто закрыть "часики"

    await callback.message.edit_text(
        TEXTS[lang_code]["language_saved"],
        parse_mode="Markdown"
    )

    await callback.message.answer(
        TEXTS[lang_code]["welcome"] + "\n\n" + TEXTS[lang_code]["main_menu_title"],
        reply_markup=main_menu_keyboard(user_id),
        parse_mode="Markdown"
    )


@dp.message(F.text)
async def handle_text(message: Message):
    """
    Обработка нажатий по кнопкам меню.
    Пока всё — заглушки.
    """
    user_id = message.from_user.id
    lang = get_lang(user_id)
    texts = TEXTS[lang]

    text = message.text.strip()

    if text == texts["btn_today_overview"]:
        await message.answer(texts["today_stub"])
    elif text == texts["btn_plan"]:
        await message.answer(texts["plan_stub"])
    elif text == texts["btn_settings"]:
        await message.answer(texts["settings_stub"])
    else:
        await message.answer(texts["unknown_command"])


# Дополнительно: /help (на всякий случай)
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Use /start to choose language and open the main menu.\n"
        "Usa /start para elegir idioma y abrir el menú principal."
    )


# ========= ЗАПУСК =========

async def main():
    print("🚀 Crypto Planner bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
