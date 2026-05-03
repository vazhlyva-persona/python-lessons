"""
Tests for the Telegram bot IDE features:
  - storage.py  — snippets and run-history tables
  - telegram_bot.py — _extract_code, REPLSession, all IDE command handlers,
                      and on_message mode dispatch
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated SQLite database; patches storage.DB_PATH for the test."""
    db = str(tmp_path / "test.db")
    monkeypatch.setattr("storage.DB_PATH", db)
    from storage import init_db
    init_db()
    return db


def make_update(text="", user_id=99001):
    msg = MagicMock()
    msg.text = text
    msg.reply_text = AsyncMock(return_value=AsyncMock())
    msg.delete = AsyncMock()
    upd = MagicMock()
    upd.effective_user.id = user_id
    upd.message = msg
    return upd


def make_context(user_data=None, args=None):
    ctx = MagicMock()
    ctx.user_data = dict(user_data) if user_data else {}
    ctx.args = list(args) if args else []
    return ctx


# ── storage — snippets ─────────────────────────────────────────────

class TestSnippetStorage:
    def test_save_and_get(self, tmp_db):
        from storage import save_snippet, get_snippet
        save_snippet("u1", "hello", "print('hi')")
        assert get_snippet("u1", "hello") == "print('hi')"

    def test_get_nonexistent_returns_none(self, tmp_db):
        from storage import get_snippet
        assert get_snippet("u1", "ghost") is None

    def test_save_overwrites_existing(self, tmp_db):
        from storage import save_snippet, get_snippet
        save_snippet("u1", "s", "v1")
        save_snippet("u1", "s", "v2")
        assert get_snippet("u1", "s") == "v2"

    def test_list_empty(self, tmp_db):
        from storage import list_snippets
        assert list_snippets("u1") == []

    def test_list_sorted_alphabetically(self, tmp_db):
        from storage import save_snippet, list_snippets
        save_snippet("u1", "b", "code_b")
        save_snippet("u1", "a", "code_a")
        names = [n for n, _ in list_snippets("u1")]
        assert names == ["a", "b"]

    def test_list_isolated_by_user(self, tmp_db):
        from storage import save_snippet, list_snippets
        save_snippet("u1", "mine", "x")
        assert list_snippets("u2") == []

    def test_delete_existing_returns_true(self, tmp_db):
        from storage import save_snippet, delete_snippet, get_snippet
        save_snippet("u1", "bye", "x")
        assert delete_snippet("u1", "bye") is True
        assert get_snippet("u1", "bye") is None

    def test_delete_nonexistent_returns_false(self, tmp_db):
        from storage import delete_snippet
        assert delete_snippet("u1", "ghost") is False


# ── storage — run history ──────────────────────────────────────────

class TestRunHistory:
    def test_add_and_get(self, tmp_db):
        from storage import add_history, get_history
        add_history("u1", "print(1)", "1")
        runs = get_history("u1")
        assert len(runs) == 1
        assert runs[0]["code"] == "print(1)"
        assert runs[0]["output"] == "1"

    def test_get_empty(self, tmp_db):
        from storage import get_history
        assert get_history("u1") == []

    def test_most_recent_first(self, tmp_db):
        from storage import add_history, get_history
        add_history("u1", "first", "1")
        add_history("u1", "second", "2")
        assert get_history("u1")[0]["code"] == "second"

    def test_capped_at_ten(self, tmp_db):
        from storage import add_history, get_history
        for i in range(15):
            add_history("u1", f"code_{i}", str(i))
        assert len(get_history("u1", limit=20)) == 10

    def test_limit_parameter(self, tmp_db):
        from storage import add_history, get_history
        for i in range(5):
            add_history("u1", f"x={i}", str(i))
        assert len(get_history("u1", limit=3)) == 3

    def test_isolated_by_user(self, tmp_db):
        from storage import add_history, get_history
        add_history("u1", "code", "out")
        assert get_history("u2") == []


# ── _extract_code ──────────────────────────────────────────────────

class TestExtractCode:
    @pytest.fixture(autouse=True)
    def _import(self):
        from telegram_bot import _extract_code
        self.f = _extract_code

    def test_plain_text_unchanged(self):
        assert self.f("print('hi')") == "print('hi')"

    def test_strips_python_fence(self):
        assert self.f("```python\nprint('hi')\n```") == "print('hi')"

    def test_strips_bare_fence(self):
        assert self.f("```\nx = 1\n```") == "x = 1"

    def test_multiline_preserved(self):
        result = self.f("```python\nx = 1\nprint(x)\n```")
        assert result == "x = 1\nprint(x)"

    def test_no_closing_fence(self):
        assert self.f("```python\nprint(1)") == "print(1)"

    def test_strips_leading_trailing_whitespace(self):
        assert self.f("  x = 1  ") == "x = 1"


# ── REPLSession ────────────────────────────────────────────────────

class TestREPLSession:
    @pytest.fixture(autouse=True)
    def _session(self):
        from telegram_bot import REPLSession
        self.REPLSession = REPLSession
        self.s = REPLSession()

    def test_expression_displays_value(self):
        out, more = self.s.push("1 + 1")
        assert "2" in out
        assert more is False

    def test_print_captured(self):
        out, _ = self.s.push("print('hello')")
        assert "hello" in out

    def test_assignment_produces_no_output(self):
        out, more = self.s.push("x = 42")
        assert out == ""
        assert more is False

    def test_state_persists_across_pushes(self):
        self.s.push("x = 99")
        out, _ = self.s.push("x")
        assert "99" in out

    def test_error_captured_not_raised(self):
        out, more = self.s.push("1 / 0")
        assert "ZeroDivisionError" in out
        assert more is False

    def test_incomplete_block_returns_needs_more(self):
        _, more = self.s.push("def f():")
        assert more is True

    def test_completed_block_is_callable(self):
        self.s.push("def f():")
        self.s.push("    return 7")
        self.s.push("")  # blank line closes the block
        out, _ = self.s.push("f()")
        assert "7" in out

    def test_new_session_is_clean(self):
        self.s.push("secret = 123")
        fresh = self.REPLSession()
        out, _ = fresh.push("secret")
        assert "NameError" in out


# ── Bot command handlers ───────────────────────────────────────────

class TestCmdRun:
    pytestmark = pytest.mark.anyio

    async def test_inline_runs_code(self):
        update  = make_update("/run print('ok')")
        context = make_context()
        with patch("telegram_bot.run_user_code", return_value=("ok", "")), \
             patch("telegram_bot.add_history"):
            from telegram_bot import cmd_run
            await cmd_run(update, context)
        assert context.user_data["last_code"] == "print('ok')"
        update.message.reply_text.assert_called()

    async def test_inline_strips_fences(self):
        update  = make_update("/run ```python\nprint(1)\n```")
        context = make_context()
        with patch("telegram_bot.run_user_code", return_value=("1", "")) as mock_run, \
             patch("telegram_bot.add_history"):
            from telegram_bot import cmd_run
            await cmd_run(update, context)
        code_arg = mock_run.call_args[0][0]
        assert "```" not in code_arg

    async def test_toggle_on(self):
        update  = make_update("/run")
        context = make_context()
        from telegram_bot import cmd_run
        await cmd_run(update, context)
        assert context.user_data["free_run_mode"] is True

    async def test_toggle_off(self):
        update  = make_update("/run")
        context = make_context({"free_run_mode": True})
        from telegram_bot import cmd_run
        await cmd_run(update, context)
        assert context.user_data["free_run_mode"] is False

    async def test_toggle_clears_repl_mode(self):
        update  = make_update("/run")
        context = make_context({"repl_mode": True})
        from telegram_bot import cmd_run
        await cmd_run(update, context)
        assert context.user_data["repl_mode"] is False

    async def test_toggle_clears_lesson_mode(self):
        update  = make_update("/run")
        context = make_context({"waiting_for_code": True})
        from telegram_bot import cmd_run
        await cmd_run(update, context)
        assert context.user_data["waiting_for_code"] is False


class TestCmdRepl:
    pytestmark = pytest.mark.anyio

    async def test_toggle_on_creates_session(self):
        from telegram_bot import cmd_repl, REPLSession
        update  = make_update("/repl")
        context = make_context()
        await cmd_repl(update, context)
        assert context.user_data["repl_mode"] is True
        assert isinstance(context.user_data["repl_session"], REPLSession)

    async def test_toggle_off_removes_session(self):
        from telegram_bot import cmd_repl, REPLSession
        update  = make_update("/repl")
        context = make_context({"repl_mode": True, "repl_session": REPLSession()})
        await cmd_repl(update, context)
        assert context.user_data["repl_mode"] is False
        assert "repl_session" not in context.user_data

    async def test_toggle_clears_free_run(self):
        from telegram_bot import cmd_repl
        update  = make_update("/repl")
        context = make_context({"free_run_mode": True})
        await cmd_repl(update, context)
        assert context.user_data["free_run_mode"] is False


class TestCmdSave:
    pytestmark = pytest.mark.anyio

    async def test_no_name_shows_usage(self):
        update  = make_update("/save")
        context = make_context(args=[])
        from telegram_bot import cmd_save
        await cmd_save(update, context)
        assert "Usage" in update.message.reply_text.call_args[0][0]

    async def test_no_code_shows_error(self):
        update  = make_update("/save snip")
        context = make_context(args=["snip"])
        from telegram_bot import cmd_save
        await cmd_save(update, context)
        assert "No code" in update.message.reply_text.call_args[0][0]

    async def test_saves_last_code(self, tmp_db):
        update  = make_update("/save snip")
        context = make_context(args=["snip"], user_data={"last_code": "x = 1"})
        from telegram_bot import cmd_save
        with patch("telegram_bot.tg_uid", return_value="tg_99"):
            with patch("telegram_bot.save_snippet") as mock_save:
                await cmd_save(update, context)
        mock_save.assert_called_once_with("tg_99", "snip", "x = 1")

    async def test_success_message_contains_name(self):
        update  = make_update("/save myfile")
        context = make_context(args=["myfile"], user_data={"last_code": "y = 2"})
        from telegram_bot import cmd_save
        with patch("telegram_bot.save_snippet"):
            await cmd_save(update, context)
        assert "myfile" in update.message.reply_text.call_args[0][0]


class TestCmdLoad:
    pytestmark = pytest.mark.anyio

    async def test_no_name_shows_usage(self):
        update  = make_update("/load")
        context = make_context(args=[])
        from telegram_bot import cmd_load
        await cmd_load(update, context)
        assert "Usage" in update.message.reply_text.call_args[0][0]

    async def test_not_found_message(self):
        update  = make_update("/load ghost")
        context = make_context(args=["ghost"])
        from telegram_bot import cmd_load
        with patch("telegram_bot.get_snippet", return_value=None):
            await cmd_load(update, context)
        assert "No snippet" in update.message.reply_text.call_args[0][0]

    async def test_found_sets_last_code(self):
        update  = make_update("/load snip")
        context = make_context(args=["snip"])
        from telegram_bot import cmd_load
        with patch("telegram_bot.get_snippet", return_value="print('loaded')"):
            await cmd_load(update, context)
        assert context.user_data["last_code"] == "print('loaded')"

    async def test_found_reply_contains_code(self):
        update  = make_update("/load snip")
        context = make_context(args=["snip"])
        from telegram_bot import cmd_load
        with patch("telegram_bot.get_snippet", return_value="x = 42"):
            await cmd_load(update, context)
        reply = update.message.reply_text.call_args[0][0]
        assert "x = 42" in reply


class TestCmdSnippets:
    pytestmark = pytest.mark.anyio

    async def test_empty_list(self):
        update  = make_update("/snippets")
        context = make_context()
        from telegram_bot import cmd_snippets
        with patch("telegram_bot.list_snippets", return_value=[]):
            await cmd_snippets(update, context)
        assert "No saved" in update.message.reply_text.call_args[0][0]

    async def test_lists_names(self):
        update  = make_update("/snippets")
        context = make_context()
        from telegram_bot import cmd_snippets
        items = [("alpha", "2024-01-01"), ("beta", "2024-01-02")]
        with patch("telegram_bot.list_snippets", return_value=items):
            await cmd_snippets(update, context)
        reply = update.message.reply_text.call_args[0][0]
        assert "alpha" in reply and "beta" in reply


class TestCmdDel:
    pytestmark = pytest.mark.anyio

    async def test_no_name_shows_usage(self):
        update  = make_update("/del")
        context = make_context(args=[])
        from telegram_bot import cmd_del
        await cmd_del(update, context)
        assert "Usage" in update.message.reply_text.call_args[0][0]

    async def test_not_found(self):
        update  = make_update("/del ghost")
        context = make_context(args=["ghost"])
        from telegram_bot import cmd_del
        with patch("telegram_bot.delete_snippet", return_value=False):
            await cmd_del(update, context)
        assert "No snippet" in update.message.reply_text.call_args[0][0]

    async def test_success(self):
        update  = make_update("/del snip")
        context = make_context(args=["snip"])
        from telegram_bot import cmd_del
        with patch("telegram_bot.delete_snippet", return_value=True):
            await cmd_del(update, context)
        assert "snip" in update.message.reply_text.call_args[0][0]


class TestCmdHistory:
    pytestmark = pytest.mark.anyio

    async def test_no_history(self):
        update  = make_update("/history")
        context = make_context()
        from telegram_bot import cmd_history
        with patch("telegram_bot.get_history", return_value=[]):
            await cmd_history(update, context)
        assert "No history" in update.message.reply_text.call_args[0][0]

    async def test_shows_code_in_reply(self):
        update  = make_update("/history")
        context = make_context()
        runs = [{"code": "print(42)", "output": "42", "ran_at": "2024-01-01"}]
        from telegram_bot import cmd_history
        with patch("telegram_bot.get_history", return_value=runs):
            await cmd_history(update, context)
        assert "print(42)" in update.message.reply_text.call_args[0][0]


class TestCmdDoc:
    pytestmark = pytest.mark.anyio

    async def test_no_name_shows_usage(self):
        update  = make_update("/doc")
        context = make_context(args=[])
        from telegram_bot import cmd_doc
        await cmd_doc(update, context)
        assert "Usage" in update.message.reply_text.call_args[0][0]

    async def test_runs_pydoc_subprocess(self):
        update  = make_update("/doc len")
        context = make_context(args=["len"])
        fake = MagicMock()
        fake.stdout = "len(obj, /)\nReturn the number of items."
        fake.stderr = ""
        from telegram_bot import cmd_doc
        with patch("telegram_bot.subprocess.run", return_value=fake):
            await cmd_doc(update, context)
        reply = update.message.reply_text.call_args[0][0]
        assert "len" in reply

    async def test_timeout_handled(self):
        import subprocess as sp
        update  = make_update("/doc os")
        context = make_context(args=["os"])
        from telegram_bot import cmd_doc
        with patch("telegram_bot.subprocess.run", side_effect=sp.TimeoutExpired("pydoc", 5)):
            await cmd_doc(update, context)
        assert "Timed out" in update.message.reply_text.call_args[0][0]


# ── on_message mode dispatch ───────────────────────────────────────

class TestOnMessage:
    pytestmark = pytest.mark.anyio

    async def test_repl_mode_pushes_to_session(self):
        from telegram_bot import REPLSession, on_message
        session = REPLSession()
        update  = make_update("1 + 1")
        context = make_context({"repl_mode": True, "repl_session": session})
        await on_message(update, context)
        update.message.reply_text.assert_called_once()

    async def test_repl_mode_creates_session_if_missing(self):
        from telegram_bot import on_message, REPLSession
        update  = make_update("x = 5")
        context = make_context({"repl_mode": True})
        await on_message(update, context)
        assert isinstance(context.user_data.get("repl_session"), REPLSession)

    async def test_free_run_mode_executes_code(self):
        update  = make_update("print('free')")
        context = make_context({"free_run_mode": True})
        from telegram_bot import on_message
        with patch("telegram_bot.run_user_code", return_value=("free", "")), \
             patch("telegram_bot.add_history"):
            await on_message(update, context)
        update.message.reply_text.assert_called()

    async def test_free_run_saves_last_code(self):
        update  = make_update("x = 1")
        context = make_context({"free_run_mode": True})
        from telegram_bot import on_message
        with patch("telegram_bot.run_user_code", return_value=("", "")), \
             patch("telegram_bot.add_history"):
            await on_message(update, context)
        assert context.user_data["last_code"] == "x = 1"

    async def test_default_mode_shows_help(self):
        update  = make_update("hello")
        context = make_context()
        from telegram_bot import on_message
        await on_message(update, context)
        reply = update.message.reply_text.call_args[0][0]
        assert "/lessons" in reply or "/run" in reply

    async def test_lesson_mode_saves_last_code(self):
        from lessons import LESSONS
        update  = make_update("x = 1")
        context = make_context({"waiting_for_code": True, "current_lesson_id": LESSONS[0]["id"]})
        from telegram_bot import on_message
        with patch("telegram_bot.check_answer_full", return_value="❌ try again"):
            await on_message(update, context)
        assert context.user_data["last_code"] == "x = 1"
