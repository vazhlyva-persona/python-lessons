"""
Tests for checker.py, lessons.py, and web_app.py.
Run with:  pytest test_app.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from lessons import LESSONS
from checker import run_user_code, _build_prompt
from web_app import app as flask_app


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


SAMPLE_LESSON = LESSONS[0]  # "Variables and Data Types"


# ── lessons.py ─────────────────────────────────────────────────────

class TestLessons:
    REQUIRED_KEYS = {"id", "title", "explanation", "example", "exercise", "hints"}

    def test_ten_lessons(self):
        assert len(LESSONS) == 10

    def test_ids_are_sequential(self):
        assert [l["id"] for l in LESSONS] == list(range(1, 11))

    def test_all_lessons_have_required_keys(self):
        for lesson in LESSONS:
            missing = self.REQUIRED_KEYS - lesson.keys()
            assert not missing, f"Lesson {lesson.get('id')} missing keys: {missing}"

    def test_titles_are_non_empty_strings(self):
        for lesson in LESSONS:
            assert isinstance(lesson["title"], str) and lesson["title"].strip()

    def test_hints_are_lists(self):
        for lesson in LESSONS:
            assert isinstance(lesson["hints"], list)

    def test_no_duplicate_ids(self):
        ids = [l["id"] for l in LESSONS]
        assert len(ids) == len(set(ids))


# ── checker.py – run_user_code ──────────────────────────────────────

class TestRunUserCode:
    def test_simple_print(self):
        out, err = run_user_code("print('hello')")
        assert out == "hello"
        assert err == ""

    def test_stdout_captured(self):
        out, err = run_user_code("print(1 + 1)")
        assert out == "2"

    def test_stderr_captured(self):
        out, err = run_user_code("raise ValueError('oops')")
        assert "ValueError" in err
        assert out == ""

    def test_syntax_error(self):
        out, err = run_user_code("def broken(")
        assert err != ""

    def test_timeout(self):
        out, err = run_user_code("while True: pass", timeout=1)
        assert "Timed out" in err

    def test_multiline_code(self):
        code = "x = 5\ny = 10\nprint(x + y)"
        out, err = run_user_code(code)
        assert out == "15"

    def test_temp_file_cleaned_up(self):
        import tempfile, os, glob
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "*.py")))
        run_user_code("print('cleanup test')")
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "*.py")))
        assert after == before


# ── checker.py – _build_prompt ─────────────────────────────────────

class TestBuildPrompt:
    def test_returns_two_items(self):
        result = _build_prompt(SAMPLE_LESSON, "x = 1", "1", "")
        assert len(result) == 2

    def test_system_is_string(self):
        system, _ = _build_prompt(SAMPLE_LESSON, "x = 1", "", "")
        assert isinstance(system, str) and len(system) > 0

    def test_messages_format(self):
        _, messages = _build_prompt(SAMPLE_LESSON, "x = 1", "", "")
        assert isinstance(messages, list)
        assert messages[0]["role"] == "user"
        assert isinstance(messages[0]["content"], str)

    def test_prompt_contains_lesson_title(self):
        _, messages = _build_prompt(SAMPLE_LESSON, "x = 1", "", "")
        assert SAMPLE_LESSON["title"] in messages[0]["content"]

    def test_prompt_contains_code(self):
        code = "name = 'Alice'"
        _, messages = _build_prompt(SAMPLE_LESSON, code, "", "")
        assert code in messages[0]["content"]

    def test_stdout_in_prompt(self):
        _, messages = _build_prompt(SAMPLE_LESSON, "", "some output", "")
        assert "some output" in messages[0]["content"]

    def test_stderr_in_prompt(self):
        _, messages = _build_prompt(SAMPLE_LESSON, "", "", "NameError")
        assert "NameError" in messages[0]["content"]

    def test_none_stdout_shows_placeholder(self):
        _, messages = _build_prompt(SAMPLE_LESSON, "", "", "")
        assert "(none)" in messages[0]["content"]


# ── web_app.py ─────────────────────────────────────────────────────

class TestWebAppRoutes:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_contains_lesson_titles(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        for lesson in LESSONS:
            assert lesson["title"] in html

    def test_check_missing_lesson(self, client):
        resp = client.post(
            "/check",
            data=json.dumps({"lesson_id": 999, "code": "x=1"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_check_empty_code(self, client):
        resp = client.post(
            "/check",
            data=json.dumps({"lesson_id": 1, "code": "   "}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_check_streams_sse(self, client):
        fake_chunks = ["Good ", "job!"]

        with patch("web_app.check_answer_stream", return_value=iter(fake_chunks)):
            resp = client.post(
                "/check",
                data=json.dumps({"lesson_id": 1, "code": "x = 1"}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        assert resp.content_type.startswith("text/event-stream")
        body = resp.data.decode()
        assert "Good " in body
        assert "job!" in body
        assert "[DONE]" in body

    def test_check_sse_error_handled(self, client):
        def boom():
            raise RuntimeError("API down")
            yield  # make it a generator

        with patch("web_app.check_answer_stream", side_effect=boom):
            resp = client.post(
                "/check",
                data=json.dumps({"lesson_id": 1, "code": "x = 1"}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        body = resp.data.decode()
        assert "Error" in body or "[DONE]" in body
