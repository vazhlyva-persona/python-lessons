"""
Telegram bot — teaches Python lessons with AI feedback.

Run:  python telegram_bot.py

Required env vars:
  TELEGRAM_BOT_TOKEN   – from @BotFather
  ANTHROPIC_API_KEY    – from console.anthropic.com
"""

import logging
import os
import textwrap

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from checker import check_answer_full
from lessons import LESSONS

logging.basicConfig(
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────

MAX_TG_LEN = 4000  # Telegram message limit (~4096; we stay under)


def split_message(text: str) -> list[str]:
    """Split long text into chunks that fit a Telegram message."""
    return textwrap.wrap(text, MAX_TG_LEN, break_long_words=False, replace_whitespace=False)


def lesson_by_id(lesson_id: int):
    return next((l for l in LESSONS if l["id"] == lesson_id), None)


def lessons_keyboard():
    """Inline keyboard with all lesson buttons (2 per row)."""
    buttons = [
        InlineKeyboardButton(f"{l['id']}. {l['title']}", callback_data=f"lesson:{l['id']}")
        for l in LESSONS
    ]
    # 2 columns
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def lesson_nav_keyboard(lesson_id: int):
    """Inline keyboard shown after a lesson — next / list."""
    buttons = []
    nxt = lesson_by_id(lesson_id + 1)
    if nxt:
        buttons.append(InlineKeyboardButton(f"Next → {nxt['title']}", callback_data=f"lesson:{nxt['id']}"))
    buttons.append(InlineKeyboardButton("📋 All lessons", callback_data="list"))
    return InlineKeyboardMarkup([buttons])


# ── Command handlers ───────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Python Lessons!*\n\n"
        "I'll walk you through Python step by step and use AI to check your answers.\n\n"
        "Use /lessons to see all topics, or /lesson 1 to jump straight in.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Available lessons:*\nTap one to begin.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=lessons_keyboard(),
    )


async def cmd_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lesson <id>"""
    try:
        lesson_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /lesson <number>  e.g. /lesson 3")
        return
    await _show_lesson(update.message, context, lesson_id)


async def cmd_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson_id = context.user_data.get("current_lesson_id")
    if not lesson_id:
        await update.message.reply_text("Start a lesson first: /lessons")
        return
    lesson = lesson_by_id(lesson_id)
    hints = lesson.get("hints", [])
    if hints:
        text = "💭 *Hints:*\n" + "\n".join(f"• {h}" for h in hints)
    else:
        text = "No hints for this lesson."
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_id = context.user_data.get("current_lesson_id", 0)
    next_lesson = lesson_by_id(current_id + 1)
    if next_lesson:
        await _show_lesson(update.message, context, next_lesson["id"])
    else:
        await update.message.reply_text("🎉 You've reached the last lesson! Great work.")


# ── Inline button handler ──────────────────────────────────────────

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        await query.message.reply_text(
            "📚 *Lessons:*", parse_mode=ParseMode.MARKDOWN, reply_markup=lessons_keyboard()
        )
    elif query.data.startswith("lesson:"):
        lesson_id = int(query.data.split(":")[1])
        await _show_lesson(query.message, context, lesson_id)


# ── Core: display a lesson ─────────────────────────────────────────

async def _show_lesson(message, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    lesson = lesson_by_id(lesson_id)
    if not lesson:
        await message.reply_text(f"Lesson {lesson_id} not found.")
        return

    context.user_data["current_lesson_id"] = lesson_id
    context.user_data["waiting_for_code"]  = True

    text = (
        f"📖 *Lesson {lesson['id']}: {lesson['title']}*\n\n"
        f"*Explanation:*\n```\n{lesson['explanation']}\n```\n\n"
        f"*Example:*\n```python\n{lesson['example']}\n```\n\n"
        f"*Exercise:*\n```\n{lesson['exercise']}\n```\n\n"
        "✏️ Send me your Python code to check it.\n"
        "Use /hint for hints · /next to skip · /lessons to pick another."
    )

    # Split if needed (unlikely but safe)
    for chunk in split_message(text):
        await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ── Core: handle code submissions ─────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive a text message — treat it as code if we're waiting for it."""
    if not context.user_data.get("waiting_for_code"):
        await update.message.reply_text(
            "Use /lessons to pick a lesson, or /lesson <number> to jump to one."
        )
        return

    lesson_id = context.user_data.get("current_lesson_id")
    lesson    = lesson_by_id(lesson_id)
    if not lesson:
        await update.message.reply_text("Something went wrong — try /lessons again.")
        return

    code = update.message.text

    thinking_msg = await update.message.reply_text("🤖 Checking your code, please wait…")

    try:
        feedback = check_answer_full(lesson, code)
    except Exception as exc:
        logger.exception("Claude API error")
        feedback = f"⚠️ Could not get feedback: {exc}"

    await thinking_msg.delete()

    # Send feedback (split if long)
    for chunk in split_message(feedback):
        await update.message.reply_text(chunk)

    # Offer navigation after correct answer
    if "✅" in feedback:
        context.user_data["waiting_for_code"] = False
        await update.message.reply_text(
            "Great job! What's next?",
            reply_markup=lesson_nav_keyboard(lesson_id),
        )
    else:
        await update.message.reply_text(
            "Give it another try! Or use /hint for hints, /next to move on."
        )


# ── Entry point ────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("lessons", cmd_lessons))
    app.add_handler(CommandHandler("lesson",  cmd_lesson))
    app.add_handler(CommandHandler("hint",    cmd_hint))
    app.add_handler(CommandHandler("next",    cmd_next))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot is running …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
