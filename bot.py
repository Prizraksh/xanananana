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
START_TEXT = "<i>speacil for РѕРґРЅРѕ beautiful СЃРѕР»РЅС‹С€РєРѕвњЁ</i>"
START_BUTTON_TEXT = "???"
START_BUTTON_PRESSED_TEXT = "РўРѕРіРґР° Р·Р°РїСѓСЃРєР°СЋ РґР»СЏ С‚РµР±СЏ РјР°Р»РµРЅСЊРєРёР№ С‚С‘РїР»С‹Р№ СЃСЋСЂРїСЂРёР·..."

MAIN_SCENE_MESSAGES: Sequence[Tuple[str, float]] = (
    ("<b>Loading...</b> СЃРѕР±РёСЂР°СЋ РґР»СЏ С‚РµР±СЏ РЅРµРјРЅРѕРіРѕ С‚РµРїР»Р°.", 1.3),
    ("РїСЂРѕРІРµСЂРєР° СЃРІСЏР·Рё: РјРѕСЏ Р»СЋР±РёРјР°СЏ РљСЃР°РЅРѕС‡РєР° РЅР° РјРµСЃС‚Рµ?", 1.5),
    ("РѕР±РЅР°СЂСѓР¶РµРЅРѕ: С‚С‹ СЃР»РёС€РєРѕРј РґРѕР±СЂР°СЏ, СЃРІРµС‚Р»Р°СЏ Рё РєСЂР°СЃРёРІР°СЏ, СЃРµСЂРґС†Рµ СѓР¶Рµ Р·Р°РЅСЏС‚Рѕ С‚РѕР±РѕР№ РЅР° 100%.", 1.8),
    ("РµСЃР»Рё С‚РµР±Рµ СЃРµР№С‡Р°СЃ РіСЂСѓСЃС‚РЅРѕ, СЌС‚Рѕ СЃРѕРѕР±С‰РµРЅРёРµ РїСЂРѕСЃС‚Рѕ С‚РёС…Рѕ С‚РµР±СЏ РѕР±РЅРёРјР°РµС‚.", 2.0),
    ("С‚С‹ РЅРµ РѕР±СЏР·Р°РЅР° Р±С‹С‚СЊ СЃРёР»СЊРЅРѕР№ РєР°Р¶РґСѓСЋ СЃРµРєСѓРЅРґСѓ.", 1.7),
    ("РёРЅРѕРіРґР° РјРѕР¶РЅРѕ РїРѕР±С‹С‚СЊ СѓСЃС‚Р°РІС€РµР№, РЅРµР¶РЅРѕР№ Рё РЅР°СЃС‚РѕСЏС‰РµР№, Рё РѕС‚ СЌС‚РѕРіРѕ С‚С‹ РЅРµ СЃС‚Р°РЅРѕРІРёС€СЊСЃСЏ РјРµРЅРµРµ РїСЂРµРєСЂР°СЃРЅРѕР№.", 2.4),
    ("СЏ РѕС‡РµРЅСЊ С…РѕС‡Сѓ, С‡С‚РѕР±С‹ РїСЂСЏРјРѕ СЃРµР№С‡Р°СЃ Сѓ С‚РµР±СЏ РїРѕСЏРІРёР»Р°СЃСЊ С…РѕС‚СЏ Р±С‹ РјР°Р»РµРЅСЊРєР°СЏ СѓР»С‹Р±РєР°.", 2.2),
    ("Рё Сѓ РјРµРЅСЏ РµСЃС‚СЊ РґР»СЏ С‚РµР±СЏ РµС‰С‘ РєРѕРµ-С‡С‚Рѕ...", 1.0),
)

AFTER_SCENE_TEXT = "Р•С‰С‘С‘С‘:"
PASSENGER_BUTTON_TEXT = "СЌС‚Рѕ С‡С‚Рѕ Р·Р° РїР°СЃСЃР°Р¶РёСЂ"
CODE_BUTTON_TEXT = "Р¶РµСЃРє РєРѕРґ"
HUG_BUTTON_TEXT = "РѕР±РЅРёРјР°СЋСЋ С‚РµР±СЏ"

PASSENGER_HEADER_TEXT = "СЌС‚Рѕ СЏ"
EXTRA_SUPPORT_MESSAGES: Sequence[Tuple[str, float]] = (
    ("С‚С‹ РїСЂР°РІРґР° РѕС‡РµРЅСЊ-РѕС‡РµРЅСЊ С†РµРЅРЅР°СЏ. РџРѕ-РЅР°СЃС‚РѕСЏС‰РµРјСѓ.", 1.5),
    ("СЃ С‚РѕР±РѕР№ РјРёСЂ СЃС‚Р°РЅРѕРІРёС‚СЃСЏ РјСЏРіС‡Рµ Рё РєСЂР°СЃРёРІРµРµ.", 1.5),
    ("РґР°Р¶Рµ РєРѕРіРґР° С‚РµР±Рµ С‚СЏР¶РµР»Рѕ, С‚С‹ РІСЃС‘ СЂР°РІРЅРѕ СѓРґРёРІРёС‚РµР»СЊРЅР°СЏ.", 1.6),
    ("СЏ Р±С‹ СЃРµР№С‡Р°СЃ РїСЂРѕСЃС‚Рѕ СЃРµР» СЂСЏРґРѕРј Рё РґРµСЂР¶Р°Р» С‚РµР±СЏ Р·Р° СЂСѓРєСѓ.", 0.6),
)

CODE_HEADER_TEXT = "Р›РѕРІРё РјР°Р»РµРЅСЊРєРёР№ Р¶РµСЃРє-РєРѕРґ"
PROGRAMMER_SECRET_CODE = (
    "<pre><code>mood = \"a little sad\"\n\n"
    "if you_are_here:\n"
    "    mood = \"better\"\n"
    "    heart += 1\n"
    "    world = \"warmer\"</code></pre>"
)
PROGRAMMER_SECRET_TEXT = (
    "Р·РґРµСЃСЊ РµСЃС‚СЊ РїРѕСЃС‚РѕСЏРЅРЅС‹Р№ СЌС„С„РµРєС‚: "
    "РєРѕРіРґР° РґСѓРјР°СЋ Рѕ С‚РµР±Рµ, РІРЅСѓС‚СЂРё СЃС‚Р°РЅРѕРІРёС‚СЃСЏ С‚РµРїР»РµРµ."
)

REPEAT_SCENE_TEXT = "РћР±РЅРёРјР°СЋСЋ. Р—Р°РїСѓСЃРєР°СЋ РІСЃС‘ Р·Р°РЅРѕРІРѕ, РґР»СЏ С‚РІРѕРµР№ СѓР»С‹Р±РєРё."
UNKNOWN_ACTION_TEXT = "РљР°Р¶РµС‚СЃСЏ, СЌС‚Р° РєРЅРѕРїРѕС‡РєР° РїРѕС‚РµСЂСЏР»Р°СЃСЊ. РќР°Р¶РјРё /start, Рё РјС‹ РІСЃС‘ РЅР°С‡РЅС‘Рј Р·Р°РЅРѕРІРѕ."

PHOTO_FILENAME = "photo.jpg"
LOVE_PHOTO_FILENAME = "photo2.jpg"
PHOTO_CAPTION = "СЃРѕР»РЅС‹С€РєРё-РєСЂРµРЅРґРµР»РµС‡РєРё I&lt;3U"
PHOTO_MISSING_TEXT = "РўСѓС‚ РґРѕР»Р¶РЅР° Р±С‹Р»Р° Р±С‹С‚СЊ РЅР°С€Р° СЃР°РјР°СЏ С‚С‘РїР»Р°СЏ С„РѕС‚РєР° рџҐє"
LOVE_PHOTO_MISSING_TEXT = "РўСѓС‚ РґРѕР»Р¶РЅР° Р±С‹С‚СЊ РІС‚РѕСЂР°СЏ С„РѕС‚РѕС‡РєР°, РЅРѕ РїРѕРєР° РЅРµ РЅР°С€Р»Р° photo2.jpg рџҐє"

GENERIC_ERROR_TEXT = "РќРµР±РѕР»СЊС€РѕР№ С‚РµС…РЅРёС‡РµСЃРєРёР№ РїС€РёРє. РџРѕРїСЂРѕР±СѓР№ РµС‰С‘ СЂР°Р·, СЏ СЂСЏРґРѕРј."
FORWARD_TEMPLATE = (
    "<b>РќРѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ Р±РѕС‚Сѓ</b>\n"
    "РћС‚: {user_name} ({user_tag})\n"
    "chat_id: <code>{chat_id}</code>\n"
    "РўРµРєСЃС‚:\n"
    "<blockquote>{message_text}</blockquote>"
)
ADMIN_CHAT_ID_FALLBACK = 1618524681


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
    """Р‘РµР·РѕРїР°СЃРЅР°СЏ РѕС‚РїСЂР°РІРєР° С‚РµРєСЃС‚Р°, С‡С‚РѕР±С‹ РјРµР»РєРёРµ РѕС€РёР±РєРё РЅРµ СЂРѕРЅСЏР»Рё Р±РѕС‚Р°."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError:
        logger.exception("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ РІ chat_id=%s", chat_id)


async def safe_edit_query_message(
    query,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Р‘РµР·РѕРїР°СЃРЅРѕРµ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёРµ СЃРѕРѕР±С‰РµРЅРёСЏ СЃ inline-РєРЅРѕРїРєР°РјРё."""
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        logger.exception("РћС€РёР±РєР° СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СЃРѕРѕР±С‰РµРЅРёСЏ: %s", exc)
    except TelegramError:
        logger.exception("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°С‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ callback-РєРЅРѕРїРєРё")


async def send_sequence_with_delay(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    messages: Sequence[Tuple[str, float]],
) -> None:
    """РџРѕСЃР»РµРґРѕРІР°С‚РµР»СЊРЅР°СЏ РѕС‚РїСЂР°РІРєР° СЃРѕРѕР±С‰РµРЅРёР№ СЃ РїР°СѓР·Р°РјРё РґР»СЏ СЌС„С„РµРєС‚Р° Р¶РёРІРѕРіРѕ СЃСЋСЂРїСЂРёР·Р°."""
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
    """Send local photo with fallback message if file is missing."""
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
        logger.exception("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ С„РѕС‚Рѕ: %s", filename)
        await safe_send_text(context=context, chat_id=chat_id, text=missing_text)


async def send_final_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Final photo from photo.jpg with graceful fallback."""
    await send_local_photo(
        context=context,
        chat_id=chat_id,
        filename=PHOTO_FILENAME,
        missing_text=PHOTO_MISSING_TEXT,
    )


async def send_love_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Photo sender for /love command (photo2.jpg)."""
    await send_local_photo(
        context=context,
        chat_id=chat_id,
        filename=LOVE_PHOTO_FILENAME,
        missing_text=LOVE_PHOTO_MISSING_TEXT,
    )


async def send_main_scene(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """РћСЃРЅРѕРІРЅР°СЏ С‚СЂРѕРіР°С‚РµР»СЊРЅР°СЏ СЃС†РµРЅР° СЃ С„РёРЅР°Р»СЊРЅРѕР№ С„РѕС‚РѕРіСЂР°С„РёРµР№."""
    await send_sequence_with_delay(context=context, chat_id=chat_id, messages=MAIN_SCENE_MESSAGES)
    await send_final_photo(context=context, chat_id=chat_id)
    await safe_send_text(
        context=context,
        chat_id=chat_id,
        text=AFTER_SCENE_TEXT,
        reply_markup=build_scene_keyboard(),
    )


async def send_extra_support(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Р№ Р±Р»РѕРє С‚С‘РїР»РѕР№ РїРѕРґРґРµСЂР¶РєРё."""
    await send_sequence_with_delay(
        context=context,
        chat_id=chat_id,
        messages=EXTRA_SUPPORT_MESSAGES,
    )


async def send_programmer_secret(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """РњРёР»С‹Р№ РїСЂРѕРіСЂР°РјРјРёСЃС‚СЃРєРёР№ Р±Р»РѕРє СЃ РєРѕРґРѕРј Рё РєРѕСЂРѕС‚РєРёРј С‚С‘РїР»С‹Рј РїРѕСЃР»Р°РЅРёРµРј."""
    secret_messages: Sequence[Tuple[str, float]] = (
        (PROGRAMMER_SECRET_CODE, 1.2),
        (PROGRAMMER_SECRET_TEXT, 0.0),
    )
    await send_sequence_with_delay(context=context, chat_id=chat_id, messages=secret_messages)


# ------------------------------ HANDLERS ------------------------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРѕРјР°РЅРґС‹ /start."""
    if update.message is None:
        return

    try:
        await update.message.reply_text(
            text=START_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=build_start_keyboard(),
        )
    except TelegramError:
        logger.exception("РћС€РёР±РєР° РїСЂРё РѕР±СЂР°Р±РѕС‚РєРµ /start")


async def love(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /love command: sends photo2.jpg."""
    if update.effective_chat is None:
        return

    await send_love_photo(context=context, chat_id=update.effective_chat.id)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Р•РґРёРЅС‹Р№ РѕР±СЂР°Р±РѕС‚С‡РёРє РІСЃРµС… inline-РєРЅРѕРїРѕРє."""
    query = update.callback_query
    if query is None:
        return

    # РЎРЅРёРјР°РµРј "С‡Р°СЃРёРєРё" РЅР° РєРЅРѕРїРєРµ.
    await query.answer()

    if query.message is None:
        return

    chat_id = query.message.chat_id
    callback_data = query.data or ""

    admin_chat_id = context.application.bot_data.get("admin_chat_id")
    if admin_chat_id and update.effective_user:
        user = update.effective_user
        user_name = html.escape(user.full_name or "Р‘РµР· РёРјРµРЅРё")
        user_tag = f"@{user.username}" if user.username else "Р±РµР· username"
        callback_note = (
            "<b>РќР°Р¶Р°С‚РёРµ РєРЅРѕРїРєРё</b>\n"
            f"РћС‚: {user_name} ({user_tag})\n"
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
    """Р›РѕРіРёСЂСѓРµС‚ РІС…РѕРґСЏС‰РёРµ СЃРѕРѕР±С‰РµРЅРёСЏ Рё, РїСЂРё РЅР°СЃС‚СЂРѕР№РєРµ, РїРµСЂРµСЃС‹Р»Р°РµС‚ РёС… Р°РґРјРёРЅСѓ."""
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

    user_name = html.escape(user.full_name or "Р‘РµР· РёРјРµРЅРё")
    user_tag = f"@{user.username}" if user.username else "Р±РµР· username"
    escaped_text = html.escape(payload)

    forward_text = FORWARD_TEMPLATE.format(
        user_name=user_name,
        user_tag=user_tag,
        chat_id=chat.id,
        message_text=f"[{message_type}] {escaped_text}",
    )
    await safe_send_text(context=context, chat_id=admin_chat_id, text=forward_text)

    # РџРµСЂРµСЃС‹Р»Р°РµРј РѕСЂРёРіРёРЅР°Р» СЃРѕРѕР±С‰РµРЅРёСЏ: С‚Р°Рє С‚С‹ РїРѕР»СѓС‡Р°РµС€СЊ Рё С„РѕС‚Рѕ, Рё С‚РµРєСЃС‚, Рё РґСЂСѓРіРёРµ РјРµРґРёР°.
    try:
        await context.bot.copy_message(
            chat_id=admin_chat_id,
            from_chat_id=chat.id,
            message_id=message.message_id,
        )
    except TelegramError:
        logger.exception(
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїРµСЂРµСЃР»Р°С‚СЊ РѕСЂРёРіРёРЅР°Р» СЃРѕРѕР±С‰РµРЅРёСЏ: source_chat_id=%s message_id=%s",
            chat.id,
            message.message_id,
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ РѕР±СЂР°Р±РѕС‚С‡РёРє РѕС€РёР±РѕРє, С‡С‚РѕР±С‹ Р±РѕС‚ РЅРµ РїР°РґР°Р» РёР·-Р·Р° РёСЃРєР»СЋС‡РµРЅРёР№."""
    logger.exception("РќРµРѕР±СЂР°Р±РѕС‚Р°РЅРЅР°СЏ РѕС€РёР±РєР°: %s", context.error)

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
            "РџРµСЂРµРјРµРЅРЅР°СЏ РѕРєСЂСѓР¶РµРЅРёСЏ BOT_TOKEN РЅРµ РЅР°Р№РґРµРЅР°. "
            "Р”РѕР±Р°РІСЊ С‚РѕРєРµРЅ Рё Р·Р°РїСѓСЃС‚Рё Р±РѕС‚Р° СЃРЅРѕРІР°."
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

    logger.info("Р‘РѕС‚ Р·Р°РїСѓС‰РµРЅ РІ polling-СЂРµР¶РёРјРµ")
    application.run_polling()


if __name__ == "__main__":
    main()

