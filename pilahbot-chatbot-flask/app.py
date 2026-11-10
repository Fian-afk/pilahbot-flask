import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from chatbot.engine import ChatbotEngine


BASE_DIR = Path(__file__).resolve().parent


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "pilahbot-local-development"),
        KNOWLEDGE_BASE=str(BASE_DIR / "knowledge_base.json"),
        MAX_MESSAGE_LENGTH=500,
    )
    if config:
        app.config.update(config)

    chatbot = ChatbotEngine.from_file(app.config["KNOWLEDGE_BASE"])

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

        return jsonify(chatbot.reply(message))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
