import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Sequence, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
)


# ----------------------------- CALLBACK DATA ----------------------------- #
CALLBACK_OPEN_SURPRISE = "open_surprise"
CALLBACK_EXTRA_SUPPORT = "extra_support"
CALLBACK_GENTLE_CODE = "gentle_code"
CALLBACK_REPEAT_SCENE = "repeat_scene"


# -------------------------------- TEXTS -------------------------------- #
START_TEXT = "<i>speacil for одно beautiful солнышко✨</i>"
START_BUTTON_TEXT = "???"
START_BUTTON_PRESSED_TEXT = "Тогда запускаю для тебя маленький тёплый сюрприз..."

MAIN_SCENE_MESSAGES: Sequence[Tuple[str, float]] = (
    ("<b>Loading...</b> собираю для тебя немного тепла.", 1.3),
    ("проверка связи: моя любимая Ксаночка на месте?", 1.5),
    ("обнаружено: ты слишком добрая, светлая и красивая, сердце уже занято тобой на 100%.", 1.8),
    ("если тебе сейчас грустно, это сообщение просто тихо тебя обнимает.", 2.0),
    ("ты не обязана быть сильной каждую секунду.", 1.7),
    ("иногда можно побыть уставшей, нежной и настоящей, и от этого ты не становишься менее прекрасной.", 2.4),
    ("я очень хочу, чтобы прямо сейчас у тебя появилась хотя бы маленькая улыбка.", 2.2),
    ("и у меня есть для тебя ещё кое-что...", 1.0),
)

AFTER_SCENE_TEXT = "Ещёёё:"
PASSENGER_BUTTON_TEXT = "это что за пассажир"
CODE_BUTTON_TEXT = "жеск код"
HUG_BUTTON_TEXT = "обнимаюю тебя"

PASSENGER_HEADER_TEXT = "это я"
EXTRA_SUPPORT_MESSAGES: Sequence[Tuple[str, float]] = (
    ("ты правда очень-очень ценная. По-настоящему.", 1.5),
    ("с тобой мир становится мягче и красивее.", 1.5),
    ("даже когда тебе тяжело, ты всё равно удивительная.", 1.6),
    ("я бы сейчас просто сел рядом и держал тебя за руку.", 0.6),
)

CODE_HEADER_TEXT = "Лови маленький жеск-код"
PROGRAMMER_SECRET_CODE = (
    "<pre><code>mood = \"a little sad\"\n\n"
    "if you_are_here:\n"
    "    mood = \"better\"\n"
    "    heart += 1\n"
    "    world = \"warmer\"</code></pre>"
)
PROGRAMMER_SECRET_TEXT = (
    "здесь есть постоянный эффект: "
    "когда думаю о тебе, внутри становится теплее."
)

REPEAT_SCENE_TEXT = "Обнимаюю. Запускаю всё заново, для твоей улыбки."
UNKNOWN_ACTION_TEXT = "Кажется, эта кнопочка потерялась. Нажми /start, и мы всё начнём заново."

PHOTO_FILENAME = "photo.jpg"
PHOTO_CAPTION = "солнышки-кренделечки I&lt;3U"
PHOTO_MISSING_TEXT = "Тут должна была быть наша самая тёплая фотка 🥺"

GENERIC_ERROR_TEXT = "Небольшой технический пшик. Попробуй ещё раз, я рядом."


# ------------------------------- LOGGING -------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------ KEYBOARDS ------------------------------- #
def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=START_BUTTON_TEXT, callback_data=CALLBACK_OPEN_SURPRISE)]]
    )


def build_scene_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=PASSENGER_BUTTON_TEXT, callback_data=CALLBACK_EXTRA_SUPPORT)],
            [InlineKeyboardButton(text=CODE_BUTTON_TEXT, callback_data=CALLBACK_GENTLE_CODE)],
            [InlineKeyboardButton(text=HUG_BUTTON_TEXT, callback_data=CALLBACK_REPEAT_SCENE)],
        ]
    )


# ------------------------------- HELPERS -------------------------------- #
async def safe_send_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Безопасная отправка текста, чтобы мелкие ошибки не роняли бота."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError:
        logger.exception("Не удалось отправить сообщение в chat_id=%s", chat_id)


async def safe_edit_query_message(
    query,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Безопасное редактирование сообщения с inline-кнопками."""
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        logger.exception("Ошибка редактирования сообщения: %s", exc)
    except TelegramError:
        logger.exception("Не удалось отредактировать сообщение callback-кнопки")


async def send_sequence_with_delay(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    messages: Sequence[Tuple[str, float]],
) -> None:
    """Последовательная отправка сообщений с паузами для эффекта живого сюрприза."""
    for text, delay_seconds in messages:
        await safe_send_text(context=context, chat_id=chat_id, text=text)
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)


# --------------------------- SCENE FUNCTIONS ---------------------------- #
async def send_final_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Финальная фотография из локального файла с мягким fallback при ошибке."""
    photo_path = Path(__file__).resolve().parent / PHOTO_FILENAME

    if not photo_path.exists():
        await safe_send_text(context=context, chat_id=chat_id, text=PHOTO_MISSING_TEXT)
        return

    try:
        with photo_path.open("rb") as photo_file:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file,
                caption=PHOTO_CAPTION,
                parse_mode=ParseMode.HTML,
            )
    except (OSError, TelegramError):
        logger.exception("Не удалось отправить финальную фотографию")
        await safe_send_text(context=context, chat_id=chat_id, text=PHOTO_MISSING_TEXT)


async def send_main_scene(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Основная трогательная сцена с финальной фотографией."""
    await send_sequence_with_delay(context=context, chat_id=chat_id, messages=MAIN_SCENE_MESSAGES)
    await send_final_photo(context=context, chat_id=chat_id)
    await safe_send_text(
        context=context,
        chat_id=chat_id,
        text=AFTER_SCENE_TEXT,
        reply_markup=build_scene_keyboard(),
    )


async def send_extra_support(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Дополнительный блок тёплой поддержки."""
    await send_sequence_with_delay(
        context=context,
        chat_id=chat_id,
        messages=EXTRA_SUPPORT_MESSAGES,
    )


async def send_programmer_secret(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Милый программистский блок с кодом и коротким тёплым посланием."""
    secret_messages: Sequence[Tuple[str, float]] = (
        (PROGRAMMER_SECRET_CODE, 1.2),
        (PROGRAMMER_SECRET_TEXT, 0.0),
    )
    await send_sequence_with_delay(context=context, chat_id=chat_id, messages=secret_messages)


# ------------------------------ HANDLERS ------------------------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    if update.message is None:
        return

    try:
        await update.message.reply_text(
            text=START_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=build_start_keyboard(),
        )
    except TelegramError:
        logger.exception("Ошибка при обработке /start")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Единый обработчик всех inline-кнопок."""
    query = update.callback_query
    if query is None:
        return

    # Снимаем "часики" на кнопке.
    await query.answer()

    if query.message is None:
        return

    chat_id = query.message.chat_id
    callback_data = query.data or ""

    if callback_data == CALLBACK_OPEN_SURPRISE:
        await safe_edit_query_message(query=query, text=START_BUTTON_PRESSED_TEXT)
        await send_main_scene(context=context, chat_id=chat_id)
        return

    if callback_data == CALLBACK_EXTRA_SUPPORT:
        await safe_edit_query_message(
            query=query,
            text=PASSENGER_HEADER_TEXT,
            reply_markup=build_scene_keyboard(),
        )
        await send_extra_support(context=context, chat_id=chat_id)
        return

    if callback_data == CALLBACK_GENTLE_CODE:
        await safe_edit_query_message(
            query=query,
            text=CODE_HEADER_TEXT,
            reply_markup=build_scene_keyboard(),
        )
        await send_programmer_secret(context=context, chat_id=chat_id)
        return

    if callback_data == CALLBACK_REPEAT_SCENE:
        await safe_edit_query_message(query=query, text=REPEAT_SCENE_TEXT)
        await send_main_scene(context=context, chat_id=chat_id)
        return

    await safe_send_text(context=context, chat_id=chat_id, text=UNKNOWN_ACTION_TEXT)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок, чтобы бот не падал из-за исключений."""
    logger.exception("Необработанная ошибка: %s", context.error)

    if isinstance(update, Update) and update.effective_chat:
        await safe_send_text(
            context=context,
            chat_id=update.effective_chat.id,
            text=GENERIC_ERROR_TEXT,
        )


# -------------------------------- MAIN --------------------------------- #
def main() -> None:
    token = '8768591351:AAHFtpDQKLO9NomP8scFEJf6YBcfCZcECT4'
    if not token:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не найдена. "
            "Добавь токен и запусти бота снова."
        )

    defaults = Defaults(parse_mode=ParseMode.HTML)
    application = ApplicationBuilder().token(token).defaults(defaults).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен в polling-режиме")
    application.run_polling()


if __name__ == "__main__":
    main()
