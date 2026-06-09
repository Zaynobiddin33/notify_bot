import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

from data import appointments_available

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("BOT_ADMIN_ID")
DB_PATH = os.getenv("BOT_DB_PATH", "users.db")
NOTIFICATION_TEXT = os.getenv("BOT_NOTIFICATION_TEXT", "Qabul Ochildi")
CHECK_INTERVAL_SECONDS = int(os.getenv("BOT_CHECK_INTERVAL_SECONDS", "300"))
USE_XVFB = os.getenv("BOT_USE_XVFB", os.getenv("BOT_USE_XVBF", "true")).lower() in (
    "1",
    "true",
    "yes",
)

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN environment variable")
if not ADMIN_ID:
    raise SystemExit("Missing BOT_ADMIN_ID environment variable")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise SystemExit("BOT_ADMIN_ID must be an integer chat ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
router = Router()

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    chat_id INTEGER
);
"""

USERNAME_REGEX = re.compile(r"^@?(?P<username>[A-Za-z0-9_]{5,32})$")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(DB_SCHEMA)


def normalize_username(username: str) -> str:
    username = username.strip()
    if username.startswith("@"):
        username = username[1:]
    return username


def validate_username(username: str) -> str:
    username = normalize_username(username)
    match = USERNAME_REGEX.match(username)
    if not match:
        raise ValueError(
            "Username must be 5-32 characters and contain only letters, numbers, and underscores"
        )
    return match.group("username")


def add_user(username: str, chat_id: int | None = None) -> None:
    username = validate_username(username)
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, chat_id) VALUES (?, ?)",
            (username, chat_id),
        )
        if chat_id is not None:
            conn.execute(
                "UPDATE users SET chat_id = ? WHERE username = ?",
                (chat_id, username),
            )


def user_exists(username: str) -> bool:
    username = validate_username(username)
    with get_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None


def update_user_chat_id(username: str, chat_id: int) -> None:
    username = validate_username(username)
    with get_connection() as conn:
        conn.execute("UPDATE users SET chat_id = ? WHERE username = ?", (chat_id, username))


def get_all_users() -> list[tuple[int | None, str, int | None]]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT id, username, chat_id FROM users ORDER BY username")
        return cursor.fetchall()


def get_registered_chat_ids() -> list[int]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT chat_id FROM users WHERE chat_id IS NOT NULL")
        return [row[0] for row in cursor.fetchall() if row[0] is not None]


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def check_appointments_with_xvfb() -> bool:
    xvfb_run = shutil.which("xvfb-run")
    if not USE_XVFB or xvfb_run is None:
        if USE_XVFB:
            logger.warning("xvfb-run was not found; running appointment check directly.")
        return appointments_available()

    script = (
        "import json; "
        "from data import appointments_available; "
        "print(json.dumps({'available': appointments_available()}))"
    )
    result = subprocess.run(
        [xvfb_run, "-a", sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "xvfb-run appointment check failed with code "
            f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    output_lines = result.stdout.strip().splitlines()
    if not output_lines:
        raise RuntimeError("xvfb-run finished successfully but produced no output")

    available = json.loads(output_lines[-1])["available"]
    if isinstance(available, list):
        return any(available)
    return bool(available)


def run_appointment_check() -> bool:
    xvfb_run = shutil.which("xvfb-run")
    if USE_XVFB and xvfb_run is not None:
        return check_appointments_with_xvfb()

    if USE_XVFB:
        logger.warning("xvfb-run was not found; running appointment check directly.")

    try:
        return appointments_available()
    except Exception as exc:
        if "headed browser without having a XServer" in str(exc):
            raise RuntimeError(
                "Playwright needs an X server. Install xvfb/xauth on the server "
                "or set PRENOTAMI_HEADLESS=true."
            ) from exc
        raise


def is_available_result(result) -> bool:
    if isinstance(result, list):
        return any(result)
    return bool(result)


@router.message(Command("start"))
async def cmd_start(message: Message):
    username = message.from_user.username
    if not username:
        await message.reply(
            "Botdan foydalanish uchun Telegram username o'rnating, "
            "keyin admin sizni bazaga qo'shishi kerak."
        )
        return

    try:
        normalized = validate_username(username)
        is_allowed = user_exists(normalized)
    except ValueError:
        await message.reply("Telegram username noto'g'ri formatda.")
        return

    if not is_allowed:
        await message.reply(
            "Siz hali bazaga qo'shilmagansiz. "
        )
        return

    try:
        update_user_chat_id(normalized, message.chat.id)
    except ValueError:
        await message.reply(
            "Your Telegram username is not valid for registration. "
            "Please set a valid username in Telegram and restart the bot."
        )
        return

    await message.reply(
        "Siz ro'yxatdan o'tdingiz. Sizga kerakli paytda xabar yuboriladi."
    )
    logger.info("Registered user %s (%s)", normalized, message.chat.id)


@router.message(Command("adduser"))
async def cmd_adduser(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Siz bot administratorski emassiz.")
        return

    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.reply("Foydalanish: /adduser @username")
        return

    try:
        username = validate_username(args[0])
    except ValueError as exc:
        await message.reply(str(exc))
        return

    add_user(username)
    await message.reply(
        f"Foydalanuvchi @{username} bazaga qo'shildi. "
        "U /start buyrug'ini ishlatgunga qadar xabar yuborib bo'lmaydi."
    )
    logger.info("Admin added user %s", username)


@router.message(Command("listusers"))
async def cmd_listusers(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Siz bot administratorski emassiz.")
        return

    users = get_all_users()
    if not users:
        await message.reply("Hozircha bazada hech kim yo'q.")
        return

    lines = [
        f"@{username} - chat_id={chat_id or 'not registered'}"
        for _id, username, chat_id in users
    ]
    await message.reply("Bazadagi foydalanuvchilar:\n" + "\n".join(lines))


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Siz bot administratorski emassiz.")
        return

    chat_ids = get_registered_chat_ids()
    await message.reply(
        f"Ro'yxatdan o'tgan foydalanuvchilar soni: {len(chat_ids)}\n"
        f"Tekshiruv oralig'i: {CHECK_INTERVAL_SECONDS} soniya"
    )


async def notify_all_users(text: str) -> None:
    chat_ids = get_registered_chat_ids()
    if not chat_ids:
        logger.info("No registered chat IDs available for notification.")
        return

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text)
        except Exception as exc:
            logger.exception("Failed to send notification to chat_id=%s: %s", chat_id, exc)


async def monitor_appointments() -> None:
    last_available = False
    logger.info("Appointment monitor started, checking every %s seconds.", CHECK_INTERVAL_SECONDS)

    while True:
        try:
            available = await asyncio.to_thread(run_appointment_check)
            is_available = is_available_result(available)
            logger.info("appointments_available returned: %s", available)

            if is_available and not last_available:
                await notify_all_users(NOTIFICATION_TEXT)

            last_available = is_available
        except Exception:
            logger.exception("Appointment availability check failed.")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def main():
    init_db()
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(monitor_appointments())

    logger.info("Bot startup complete.")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
