"""
Shared answer-checking logic used by both the web app and Telegram bot.
"""

import os
import sys
import subprocess
import tempfile
import anthropic


def run_user_code(code: str, timeout: int = 10) -> tuple:
    """Execute student code in a subprocess; return (stdout, stderr)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, fname],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "Timed out after 10 seconds — check for infinite loops."
    except Exception as exc:
        return "", str(exc)
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


def _build_prompt(lesson: dict, code: str, stdout: str, stderr: str) -> tuple:
    system = (
        "You are a friendly, encouraging Python tutor reviewing a student's solution.\n"
        "Respond with:\n"
        "1. ✅ CORRECT or ❌ INCORRECT — clear and first\n"
        "2. What the student did well\n"
        "3. If wrong: exactly what is broken and how to fix it (include a short code snippet)\n"
        "4. One concise best-practice tip\n"
        "Keep the whole reply under 220 words. Be warm and constructive."
    )
    user = (
        f"Lesson: {lesson['title']}\n\n"
        f"Exercise:\n{lesson['exercise']}\n\n"
        f"Student's code:\n```python\n{code}\n```\n\n"
        f"Output when run:\n{stdout or '(none)'}\n\n"
        f"Errors:\n{stderr or '(none)'}\n\n"
        "Please evaluate."
    )
    return system, [{"role": "user", "content": user}]


def check_answer_stream(lesson: dict, code: str):
    """Yield text chunks from Claude (for web SSE streaming)."""
    stdout, stderr = run_user_code(code)
    system, messages = _build_prompt(lesson, code, stdout, stderr)
    client = anthropic.Anthropic()
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def check_answer_full(lesson: dict, code: str) -> str:
    """Return the complete evaluation text (for Telegram)."""
    return "".join(check_answer_stream(lesson, code))
