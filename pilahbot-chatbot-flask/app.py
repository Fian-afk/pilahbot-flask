import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from chatbot.database import (
    get_statistics,
    initialize_database,
    record_question,
    refresh_scores,
)
from chatbot.engine import DEFAULT_THRESHOLD, ChatbotEngine


BASE_DIR = Path(__file__).resolve().parent


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "pilahbot-local-development"),
        KNOWLEDGE_BASE=str(BASE_DIR / "knowledge_base.json"),
        DATABASE=str(BASE_DIR / "instance" / "pilahbot.sqlite3"),
        THRESHOLD=float(os.environ.get("THRESHOLD", str(DEFAULT_THRESHOLD))),
        MAX_MESSAGE_LENGTH=500,
    )
    if config:
        app.config.update(config)

    initialize_database(app.config["DATABASE"])
    chatbot = ChatbotEngine.from_file(
        app.config["KNOWLEDGE_BASE"],
        threshold=app.config["THRESHOLD"],
    )
    refresh_scores(app.config["DATABASE"], lambda message: chatbot.reply(message)["score"])

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            chatbot=chatbot.knowledge,
            suggestions=[
                "Botol plastik termasuk sampah apa?",
                "Bagaimana membuat kompos?",
                "Baterai bekas dibuang ke mana?",
            ],
        )

    @app.get("/statistik")
    def statistics():
        return render_template(
            "statistics.html",
            statistics=get_statistics(app.config["DATABASE"]),
            threshold=app.config["THRESHOLD"],
        )

    @app.post("/api/chat")
    def chat():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Kirim pesan dalam format JSON."}), 400

        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "Pesan tidak boleh kosong."}), 400
        message = message.strip()
        if len(message) > app.config["MAX_MESSAGE_LENGTH"]:
            return jsonify({
                "error": f"Pesan maksimal {app.config['MAX_MESSAGE_LENGTH']} karakter."
            }), 400

        result = chatbot.reply(message)
        if "visitor_id" not in session:
            session["visitor_id"] = uuid.uuid4().hex
        record_question(
            app.config["DATABASE"],
            session["visitor_id"],
            message,
            result,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return jsonify(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
