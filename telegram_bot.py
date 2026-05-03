"""
Telegram bot — teaches Python lessons with AI feedback,
and doubles as a lightweight Python IDE.

Run:  python telegram_bot.py

Required env vars:
  TELEGRAM_BOT_TOKEN   – from @BotFather
  ANTHROPIC_API_KEY    – from console.anthropic.com
"""

import code
import contextlib
import io
import logging
import os
import subprocess
import sys
import tempfile
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

from checker import check_answer_full, run_user_code
from lessons import LESSONS
from storage import (
    add_history,
    delete_snippet,
    get_done,
    get_history,
    get_snippet,
    init_db,
    list_snippets,
    mark_done,
    reset_progress,
    save_snippet,
)

init_db()

logging.basicConfig(
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────

MAX_TG_LEN = 4000  # Telegram message limit (~4096; we stay under)


# ── Helpers ────────────────────────────────────────────────────────

def split_message(text: str) -> list[str]:
    return textwrap.wrap(text, MAX_TG_LEN, break_long_words=False, replace_whitespace=False)


def tg_uid(update: Update) -> str:
    return f"tg_{update.effective_user.id}"


def lesson_by_id(lesson_id: int):
    return next((l for l in LESSONS if l["id"] == lesson_id), None)


def lessons_keyboard():
    buttons = [
        InlineKeyboardButton(f"{l['id']}. {l['title']}", callback_data=f"lesson:{l['id']}")
        for l in LESSONS
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def lesson_nav_keyboard(lesson_id: int):
    buttons = []
    nxt = lesson_by_id(lesson_id + 1)
    if nxt:
        buttons.append(InlineKeyboardButton(f"Next → {nxt['title']}", callback_data=f"lesson:{nxt['id']}"))
    buttons.append(InlineKeyboardButton("📋 All lessons", callback_data="list"))
    return InlineKeyboardMarkup([buttons])


def _extract_code(text: str) -> str:
    """Strip markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop ```python or ``` header
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


async def _run_and_reply(message, uid: str, code_str: str) -> None:
    """Execute code, show output, save to history."""
    stdout, stderr = run_user_code(code_str)
    if stderr:
        reply = f"❌ *Error:*\n```\n{stderr[:800]}\n```"
        combined = f"ERROR:\n{stderr}"
    elif stdout:
        reply = f"✅ *Output:*\n```\n{stdout[:800]}\n```"
        combined = stdout
    else:
        reply = "✅ *(no output)*"
        combined = ""
    add_history(uid, code_str, combined[:1000])
    for chunk in split_message(reply):
        await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ── REPL session ───────────────────────────────────────────────────

class REPLSession:
    """In-process interactive Python session (variables persist between pushes)."""

    def __init__(self):
        self.console = code.InteractiveConsole()
        self.needs_more = False

    def push(self, text: str) -> tuple[str, bool]:
        """Push one or more lines; return (captured output, needs_more)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            for line in text.split("\n"):
                try:
                    self.needs_more = self.console.push(line)
                except SystemExit:
                    self.needs_more = False
        return buf.getvalue(), self.needs_more


# ── Command handlers — lessons ─────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    done  = get_done(tg_uid(update))
    total = len(LESSONS)
    count = len(done)
    await update.message.reply_text(
        "👋 *Welcome to Python Lessons!*\n\n"
        "Learn Python step by step with AI-checked exercises.\n"
        f"Progress: *{count} / {total}* lessons completed.\n\n"
        "*📚 Lesson commands:*\n"
        "`/lessons` — pick a lesson\n"
        "`/lesson 3` — jump to lesson 3\n"
        "`/hint` — hint for current exercise\n"
        "`/next` — skip to next lesson\n"
        "`/progress` — completion overview\n"
        "`/reset` — start over\n\n"
        "*💻 IDE commands:*\n"
        "`/run` — toggle free code runner\n"
        "`/run <code>` — run a one-liner inline\n"
        "`/repl` — toggle stateful REPL (vars persist)\n"
        "`/save <name>` — save last code as snippet\n"
        "`/load <name>` — show & restore a snippet\n"
        "`/snippets` — list your saved snippets\n"
        "`/del <name>` — delete a snippet\n"
        "`/format` — auto-format last code with black\n"
        "`/doc <name>` — Python docs (e.g. `/doc len`)\n"
        "`/history` — last 5 code runs",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Available lessons:*\nTap one to begin.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=lessons_keyboard(),
    )


async def cmd_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    hints  = lesson.get("hints", [])
    text   = ("💭 *Hints:*\n" + "\n".join(f"• {h}" for h in hints)) if hints else "No hints for this lesson."
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    done  = get_done(tg_uid(update))
    total = len(LESSONS)
    lines = [f"{'✅' if l['id'] in done else '⬜'} {l['id']}. {l['title']}" for l in LESSONS]
    text  = (
        f"📊 *Your progress: {len(done)} / {total}*\n\n"
        + "\n".join(lines)
        + "\n\nUse /reset to start over."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_progress(tg_uid(update))
    await update.message.reply_text("🔄 Progress reset. Use /lessons to start fresh.")


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_id  = context.user_data.get("current_lesson_id", 0)
    next_lesson = lesson_by_id(current_id + 1)
    if next_lesson:
        await _show_lesson(update.message, context, next_lesson["id"])
    else:
        await update.message.reply_text("🎉 You've reached the last lesson! Great work.")


# ── Command handlers — IDE ─────────────────────────────────────────

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run code inline (/run <code>) or toggle free-run mode."""
    raw   = update.message.text or ""
    parts = raw.split(None, 1)
    inline = _extract_code(parts[1]) if len(parts) > 1 else ""

    if inline:
        context.user_data["last_code"] = inline
        await _run_and_reply(update.message, tg_uid(update), inline)
        return

    was_on = context.user_data.get("free_run_mode", False)
    context.user_data["free_run_mode"]    = not was_on
    context.user_data["repl_mode"]        = False
    context.user_data["waiting_for_code"] = False

    if not was_on:
        await update.message.reply_text(
            "▶️ *Free-run mode ON.*\n"
            "Send any Python code to execute it.\n"
            "Send `/run` again to exit, or `/repl` for a stateful REPL.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text("⏹ Free-run mode OFF.")


async def cmd_repl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle stateful interactive REPL (variables survive between messages)."""
    was_on = context.user_data.get("repl_mode", False)
    context.user_data["repl_mode"]        = not was_on
    context.user_data["free_run_mode"]    = False
    context.user_data["waiting_for_code"] = False

    if not was_on:
        context.user_data["repl_session"] = REPLSession()
        await update.message.reply_text(
            "🔁 *REPL mode ON.*  Variables persist between messages.\n"
            "Send `/repl` to exit and clear the session.\n"
            "Multi-line blocks work — just send the whole block at once.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        context.user_data.pop("repl_session", None)
        await update.message.reply_text("⏹ REPL session ended.")


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip() if context.args else ""
    if not name:
        await update.message.reply_text("Usage: `/save <name>`  — saves your last run/submitted code", parse_mode=ParseMode.MARKDOWN)
        return
    last = context.user_data.get("last_code", "")
    if not last:
        await update.message.reply_text("No code to save yet. Run something first.")
        return
    save_snippet(tg_uid(update), name, last)
    await update.message.reply_text(f"💾 Saved as *{name}*.", parse_mode=ParseMode.MARKDOWN)


async def cmd_load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip() if context.args else ""
    if not name:
        await update.message.reply_text("Usage: `/load <name>`", parse_mode=ParseMode.MARKDOWN)
        return
    snippet = get_snippet(tg_uid(update), name)
    if snippet is None:
        await update.message.reply_text(f"No snippet named *{name}*. Use /snippets to list all.", parse_mode=ParseMode.MARKDOWN)
        return
    context.user_data["last_code"] = snippet
    await update.message.reply_text(
        f"📂 *{name}:*\n```python\n{snippet}\n```",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_snippets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = list_snippets(tg_uid(update))
    if not items:
        await update.message.reply_text("No saved snippets yet. Use `/save <name>` after running code.", parse_mode=ParseMode.MARKDOWN)
        return
    lines = [f"• `{name}` — {ts[:10]}" for name, ts in items]
    await update.message.reply_text(
        "💾 *Your snippets:*\n" + "\n".join(lines) + "\n\nUse `/load <name>` to retrieve.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip() if context.args else ""
    if not name:
        await update.message.reply_text("Usage: `/del <name>`", parse_mode=ParseMode.MARKDOWN)
        return
    if delete_snippet(tg_uid(update), name):
        await update.message.reply_text(f"🗑 Deleted *{name}*.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"No snippet named *{name}*.")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    runs = get_history(tg_uid(update))
    if not runs:
        await update.message.reply_text("No history yet. Run some code first.")
        return
    parts = ["🕐 *Last runs:*\n"]
    for i, run in enumerate(runs, 1):
        code_preview = run["code"][:80].replace("\n", " ↵ ")
        out_preview  = (run["output"] or "(no output)")[:60].replace("\n", " ↵ ")
        parts.append(f"*{i}.* `{code_preview}`\n→ {out_preview}\n")
    await update.message.reply_text("\n".join(parts), parse_mode=ParseMode.MARKDOWN)


async def cmd_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).strip() if context.args else ""
    if not name:
        await update.message.reply_text("Usage: `/doc <name>`  e.g. `/doc len` or `/doc str.split`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pydoc", name],
            capture_output=True, text=True, timeout=5,
        )
        text = (result.stdout or result.stderr or "No documentation found.").strip()
    except subprocess.TimeoutExpired:
        text = "Timed out fetching docs."
    text = text[:2500]
    for chunk in split_message(f"📖 *`{name}`*\n```\n{text}\n```"):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


async def cmd_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last = context.user_data.get("last_code", "")
    if not last:
        await update.message.reply_text("No code to format. Run or load something first.")
        return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(last)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "--quiet", fname],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            with open(fname, encoding="utf-8") as f:
                formatted = f.read().strip()
            context.user_data["last_code"] = formatted
            await update.message.reply_text(
                f"✨ *Formatted:*\n```python\n{formatted}\n```",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text(
                f"⚠️ Could not format:\n```\n{result.stderr[:400]}\n```",
                parse_mode=ParseMode.MARKDOWN,
            )
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


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
    context.user_data["free_run_mode"]     = False
    context.user_data["repl_mode"]         = False

    text = (
        f"📖 *Lesson {lesson['id']}: {lesson['title']}*\n\n"
        f"*Explanation:*\n```\n{lesson['explanation']}\n```\n\n"
        f"*Example:*\n```python\n{lesson['example']}\n```\n\n"
        f"*Exercise:*\n```\n{lesson['exercise']}\n```\n\n"
        "✏️ Send me your Python code to check it.\n"
        "Use /hint for hints · /next to skip · /lessons to pick another."
    )
    for chunk in split_message(text):
        await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ── Core: handle all text messages ────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid  = tg_uid(update)

    # REPL mode — push each message to the interactive session
    if context.user_data.get("repl_mode"):
        session: REPLSession = context.user_data.setdefault("repl_session", REPLSession())
        output, needs_more = session.push(text)
        prompt = "... " if needs_more else ">>> "
        if output:
            await update.message.reply_text(
                f"```\n{output.rstrip()}\n```", parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(f"`{prompt}`", parse_mode=ParseMode.MARKDOWN)
        return

    # Free-run mode — execute as Python
    if context.user_data.get("free_run_mode"):
        code_str = _extract_code(text)
        context.user_data["last_code"] = code_str
        await _run_and_reply(update.message, uid, code_str)
        return

    # Lesson mode — AI-check the answer
    if context.user_data.get("waiting_for_code"):
        lesson_id = context.user_data.get("current_lesson_id")
        lesson    = lesson_by_id(lesson_id)
        if not lesson:
            await update.message.reply_text("Something went wrong — try /lessons again.")
            return

        context.user_data["last_code"] = text
        thinking_msg = await update.message.reply_text("🤖 Checking your code, please wait…")
        try:
            feedback = check_answer_full(lesson, text)
        except Exception as exc:
            logger.exception("Claude API error")
            feedback = f"⚠️ Could not get feedback: {exc}"
        await thinking_msg.delete()

        for chunk in split_message(feedback):
            await update.message.reply_text(chunk)

        if "✅" in feedback:
            mark_done(uid, lesson_id)
            context.user_data["waiting_for_code"] = False
            done  = get_done(uid)
            count = len(done)
            total = len(LESSONS)
            await update.message.reply_text(
                f"Great job! Progress: {count}/{total} lessons done. What's next?",
                reply_markup=lesson_nav_keyboard(lesson_id),
            )
        else:
            await update.message.reply_text(
                "Give it another try! Or use /hint for hints, /next to move on."
            )
        return

    await update.message.reply_text(
        "Use /lessons to pick a lesson, /run to execute free code, or /repl for interactive Python."
    )


# ── Entry point ────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    # Lesson commands
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("lessons",  cmd_lessons))
    app.add_handler(CommandHandler("lesson",   cmd_lesson))
    app.add_handler(CommandHandler("hint",     cmd_hint))
    app.add_handler(CommandHandler("next",     cmd_next))
    app.add_handler(CommandHandler("progress", cmd_progress))
    app.add_handler(CommandHandler("reset",    cmd_reset))

    # IDE commands
    app.add_handler(CommandHandler("run",      cmd_run))
    app.add_handler(CommandHandler("repl",     cmd_repl))
    app.add_handler(CommandHandler("save",     cmd_save))
    app.add_handler(CommandHandler("load",     cmd_load))
    app.add_handler(CommandHandler("snippets", cmd_snippets))
    app.add_handler(CommandHandler("del",      cmd_del))
    app.add_handler(CommandHandler("format",   cmd_format))
    app.add_handler(CommandHandler("doc",      cmd_doc))
    app.add_handler(CommandHandler("history",  cmd_history))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot is running …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
