"""
Flask web application — serves the lesson UI and handles answer checking via SSE.
"""

import json
import os
import uuid

from flask import Flask, Response, make_response, render_template, request, stream_with_context

from checker import check_answer_stream
from lessons import LESSONS
from storage import get_done, init_db, mark_done

app = Flask(__name__)
init_db()

_COOKIE = "py_user_id"
_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 year


def _user_id() -> str:
    uid = request.cookies.get(_COOKIE)
    return uid if uid else str(uuid.uuid4())


def _set_cookie(resp, uid: str):
    resp.set_cookie(_COOKIE, uid, max_age=_COOKIE_AGE, samesite="Lax")
    return resp


@app.route("/")
def index():
    uid  = _user_id()
    done = sorted(get_done(uid))
    resp = make_response(render_template("index.html", lessons=LESSONS, done=done))
    return _set_cookie(resp, uid)


@app.route("/progress", methods=["GET"])
def get_progress():
    uid  = _user_id()
    done = sorted(get_done(uid))
    resp = make_response({"done": done})
    return _set_cookie(resp, uid)


@app.route("/progress", methods=["POST"])
def save_progress():
    uid = request.cookies.get(_COOKIE)
    if not uid:
        return {"error": "No session"}, 400
    data      = request.get_json(force=True)
    lesson_id = data.get("lesson_id")
    if not isinstance(lesson_id, int):
        return {"error": "Invalid lesson_id"}, 400
    mark_done(uid, lesson_id)
    return {"ok": True}


@app.route("/progress/reset", methods=["POST"])
def reset():
    from storage import reset_progress
    uid = request.cookies.get(_COOKIE)
    if uid:
        reset_progress(uid)
    return {"ok": True}


@app.route("/check", methods=["POST"])
def check():
    data      = request.get_json(force=True)
    lesson_id = data.get("lesson_id")
    code      = data.get("code", "").strip()

    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    if not lesson:
        return {"error": "Lesson not found"}, 404
    if not code:
        return {"error": "No code provided"}, 400

    def generate():
        try:
            for chunk in check_answer_stream(lesson, code):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'text': f'Error: {exc}'})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
