import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import (
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    SYSTEM_PROMPT,
    TEMPERATURE,
    WELCOME_MESSAGE,
)

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
MAX_HISTORY = 20
MAX_MESSAGE_LENGTH = 2000

client = genai.Client(api_key=API_KEY) if API_KEY else None

generation_config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    temperature=TEMPERATURE,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)


def build_contents(history):
    contents = []
    for item in history[-MAX_HISTORY:]:
        role = "model" if item.get("role") == "bot" else "user"
        text = str(item.get("text", "")).strip()[:MAX_MESSAGE_LENGTH]
        if text:
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    return contents


@app.route("/")
def index():
    return render_template("index.html", welcome=WELCOME_MESSAGE)


@app.route("/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({"error": "The server is missing its Gemini API key."}), 500

    data = request.get_json(silent=True) or {}
    history = data.get("messages")

    if not isinstance(history, list) or not history:
        return jsonify({"error": "Please type a message first."}), 400

    contents = build_contents(history)
    if not contents or contents[-1].role != "user":
        return jsonify({"error": "Please type a message first."}), 400

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=generation_config,
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = "I couldn't come up with an answer. Could you rephrase your question?"
        return jsonify({"reply": reply})
    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "Something went wrong. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True)
