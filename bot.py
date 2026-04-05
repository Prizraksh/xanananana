import asyncio
import html
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
    MessageHandler,
    filters,
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
    ("Проверка связи: моя любимая Ксаночка на месте?", 1.5),
    ("Обнаружено: ты слишком добрая, светлая и красивая, сердце уже занято тобой на 100%.", 1.8),
    ("Если тебе сейчас грустно, это сообщение просто тихо тебя обнимает.", 2.0),
    ("Ты не обязана быть сильной каждую секунду.", 1.7),
    ("Иногда можно побыть уставшей, нежной и настоящей, и от этого ты не становишься менее прекрасной.", 2.4),
    ("Я очень хочу, чтобы прямо сейчас у тебя появилась хотя бы маленькая улыбка.", 2.2),
    ("И у меня есть для тебя ещё кое-что...", 1.0),
)

AFTER_SCENE_TEXT = "Если хочешь, вот ещё три кнопочки с заботой:"
PASSENGER_BUTTON_TEXT = "это что за пассажир"
CODE_BUTTON_TEXT = "жеск код"
HUG_BUTTON_TEXT = "обнимаюю тебя"

PASSENGER_HEADER_TEXT = "Это пассажир, который очень тебя бережёт 🤍"
EXTRA_SUPPORT_MESSAGES: Sequence[Tuple[str, float]] = (
    ("Ты правда очень-очень ценная. По-настоящему.", 1.5),
    ("С тобой мир становится мягче и красивее.", 1.5),
    ("Даже когда тебе тяжело, ты всё равно удивительная.", 1.6),
    ("Я бы сейчас просто сел рядом и держал тебя за руку.", 0.6),
)

CODE_HEADER_TEXT = "Лови маленький жеск-код от влюблённого программиста:"
PROGRAMMER_SECRET_CODE = (
    "<pre><code>mood = \"a little sad\"\n\n"
    "if you_are_here:\n"
    "    mood = \"better\"\n"
    "    heart += 1\n"
    "    world = \"warmer\"</code></pre>"
)
PROGRAMMER_SECRET_TEXT = (
    "Здесь есть постоянный эффект: когда думаю о тебе, внутри становится теплее."
)

REPEAT_SCENE_TEXT = "Обнимаюю. Запускаю всё заново, для твоей улыбки."
UNKNOWN_ACTION_TEXT = "Кажется, эта кнопочка потерялась. Нажми /start, и мы всё начнём заново."

PHOTO_FILENAME = "photo.jpg"
LOVE_PHOTO_FILENAME = "photo2.jpg"
PHOTO_CAPTION = "солнышки-кренделечки I&lt;3U"
PHOTO_MISSING_TEXT = "Тут должна была быть наша самая тёплая фотка 🥺"
LOVE_PHOTO_MISSING_TEXT = "Тут должна быть вторая фоточка, но пока не нашла photo2.jpg 🥺"

GENERIC_ERROR_TEXT = "Небольшой технический пшик. Попробуй ещё раз, я рядом."
FORWARD_TEMPLATE = (
    "<b>Новое сообщение боту</b>\n"
    "От: {user_name} ({user_tag})\n"
    "chat_id: <code>{chat_id}</code>\n"
    "Текст:\n"
    "<blockquote>{message_text}</blockquote>"
)

ADMIN_CHAT_ID_FALLBACK = 1618524681
HARDCODED_TOKEN = "8768591351:AAHFtpDQKLO9NomP8scFEJf6YBcfCZcECT4"


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
async def send_local_photo(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    filename: str,
    missing_text: str,
) -> None:
    """Отправка локальной фотографии с fallback-текстом при отсутствии файла."""
    photo_path = Path(__file__).resolve().parent / filename

    if not photo_path.exists():
        await safe_send_text(context=context, chat_id=chat_id, text=missing_text)
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
        logger.exception("Не удалось отправить фото: %s", filename)
        await safe_send_text(context=context, chat_id=chat_id, text=missing_text)


async def send_final_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Финальная фотография из photo.jpg."""
    await send_local_photo(
        context=context,
        chat_id=chat_id,
        filename=PHOTO_FILENAME,
        missing_text=PHOTO_MISSING_TEXT,
    )


async def send_love_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Фотография для команды /love из photo2.jpg."""
    await send_local_photo(
        context=context,
        chat_id=chat_id,
        filename=LOVE_PHOTO_FILENAME,
        missing_text=LOVE_PHOTO_MISSING_TEXT,
    )


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


async def love(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /love: отправляет photo2.jpg."""
    if update.effective_chat is None:
        return
    await send_love_photo(context=context, chat_id=update.effective_chat.id)


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

    admin_chat_id = context.application.bot_data.get("admin_chat_id")
    if admin_chat_id and update.effective_user:
        user = update.effective_user
        user_name = html.escape(user.full_name or "Без имени")
        user_tag = f"@{user.username}" if user.username else "без username"
        callback_note = (
            "<b>Нажатие кнопки</b>\n"
            f"От: {user_name} ({user_tag})\n"
            f"chat_id: <code>{chat_id}</code>\n"
            f"callback_data: <code>{html.escape(callback_data)}</code>"
        )
        await safe_send_text(context=context, chat_id=admin_chat_id, text=callback_note)

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


async def capture_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует входящие сообщения и, при настройке, пересылает их админу."""
    if update.message is None or update.effective_chat is None or update.effective_user is None:
        return

    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    message_type = "unknown"
    payload = ""
    if message.text:
        message_type = "text"
        payload = message.text
    elif message.caption:
        message_type = "caption"
        payload = message.caption
    elif message.sticker:
        message_type = "sticker"
        payload = f"emoji={message.sticker.emoji or ''}"
    elif message.photo:
        message_type = "photo"
        payload = "photo received"
    elif message.voice:
        message_type = "voice"
        payload = "voice received"
    elif message.video:
        message_type = "video"
        payload = "video received"
    elif message.audio:
        message_type = "audio"
        payload = "audio received"
    elif message.document:
        message_type = "document"
        payload = f"file={message.document.file_name or 'unknown'}"
    else:
        payload = "unsupported message type"

    logger.info(
        "Incoming message: user_id=%s chat_id=%s username=%s type=%s payload=%s",
        user.id,
        chat.id,
        user.username,
        message_type,
        payload,
    )

    admin_chat_id = context.application.bot_data.get("admin_chat_id")
    if not admin_chat_id:
        return

    user_name = html.escape(user.full_name or "Без имени")
    user_tag = f"@{user.username}" if user.username else "без username"
    escaped_text = html.escape(payload)

    forward_text = FORWARD_TEMPLATE.format(
        user_name=user_name,
        user_tag=user_tag,
        chat_id=chat.id,
        message_text=f"[{message_type}] {escaped_text}",
    )
    await safe_send_text(context=context, chat_id=admin_chat_id, text=forward_text)

    # Пересылаем оригинал сообщения: так ты получаешь и фото, и текст, и другие медиа.
    try:
        await context.bot.copy_message(
            chat_id=admin_chat_id,
            from_chat_id=chat.id,
            message_id=message.message_id,
        )
    except TelegramError:
        logger.exception(
            "Не удалось переслать оригинал сообщения: source_chat_id=%s message_id=%s",
            chat.id,
            message.message_id,
        )


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
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        token = HARDCODED_TOKEN
    if not token:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не найдена. Добавь токен и запусти бота снова."
        )

    defaults = Defaults(parse_mode=ParseMode.HTML)
    application = ApplicationBuilder().token(token).defaults(defaults).build()

    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    if admin_chat_id_raw:
        try:
            application.bot_data["admin_chat_id"] = int(admin_chat_id_raw)
            logger.info("Forwarding incoming messages enabled: ADMIN_CHAT_ID=%s", admin_chat_id_raw)
        except ValueError:
            logger.warning("ADMIN_CHAT_ID must be numeric. Forwarding is disabled.")
    else:
        application.bot_data["admin_chat_id"] = ADMIN_CHAT_ID_FALLBACK
        logger.info(
            "ADMIN_CHAT_ID is not set. Using fallback admin id=%s",
            ADMIN_CHAT_ID_FALLBACK,
        )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("love", love))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.ALL, capture_user_message))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен в polling-режиме")
    application.run_polling()


if __name__ == "__main__":
    main()
