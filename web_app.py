"""
Flask web application — serves the lesson UI and handles answer checking via SSE.
"""

import json
import os

from flask import Flask, Response, render_template, request, stream_with_context

from checker import check_answer_stream
from lessons import LESSONS

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", lessons=LESSONS)


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    lesson_id = data.get("lesson_id")
    code = data.get("code", "").strip()

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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
