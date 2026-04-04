from flask import Flask, render_template, request, jsonify, session
import os
from eligibility_engine import (
    load_knowledge_base, get_ai_response,
    detect_state, detect_intent, STATE_URLS, STATE_NAME_TO_CODE
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")
knowledge_base = load_knowledge_base()

@app.route("/")
def index():
    session["conversation_history"] = []
    session["last_topic"] = ""
    session["last_state"] = None
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = data.get("question", "").strip()

    if not user_question:
        return jsonify({"error": "Please enter a question"}), 400

    conversation_history = session.get("conversation_history", [])
    last_topic = session.get("last_topic", "")

    # Step 1: Check intent — only for single-word abbreviations
    intent = detect_intent(user_question)

    if intent["type"] == "out_of_scope":
        return jsonify({
            "answer": "I specialize in U.S. health insurance benefits — Medicaid, ACA Marketplace, and CHIP. I'm not able to help with that topic, but happy to answer any health coverage questions!",
            "sources": [],
            "clarification": None
        })

    # Single-word abbreviation — confirm before expanding
    if intent["type"] == "abbreviation":
        return jsonify({
            "answer": None,
            "sources": [],
            "clarification": {
                "message": f"Did you mean information about {intent['clarification']}?",
                "expanded_query": intent["expanded_query"],
                "label": intent["clarification"]
            }
        })

    # Step 2: Check if user is specifying a state
    # This handles both "New York" and "NY" typed naturally
    state_code = detect_state(user_question)

    # If user typed JUST a state name/code (e.g. "NY" or "California")
    # treat it as requesting state-specific info about the last topic
    question_words = user_question.strip().split()
    is_just_state = (
        state_code and
        len(question_words) <= 3 and
        last_topic  # we have a previous topic to apply it to
    )

    if is_just_state:
        # User typed a state — apply it to the last topic
        state_name = STATE_URLS[state_code]["name"]
        question_to_ask = f"{last_topic} — specifically for {state_name}"
        session["last_state"] = state_code
    else:
        # New question — update topic, clear state context
        question_to_ask = user_question
        session["last_topic"] = user_question
        session["last_state"] = state_code  # might be None

    answer, sources = get_ai_response(
        question_to_ask,
        conversation_history,
        knowledge_base,
        state_code=state_code,
        last_topic=last_topic if is_just_state else None
    )

    conversation_history.append({"role": "user", "content": user_question})
    conversation_history.append({"role": "assistant", "content": answer})
    session["conversation_history"] = conversation_history[-20:]

    return jsonify({
        "answer": answer,
        "sources": sources,
        "clarification": None,
        "state_name": STATE_URLS[state_code]["name"] if state_code else None
    })

@app.route("/reset", methods=["POST"])
def reset():
    session["conversation_history"] = []
    session["last_topic"] = ""
    session["last_state"] = None
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)