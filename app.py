from flask import Flask, render_template, request, jsonify, session
import os
from eligibility_engine import (
    load_knowledge_base, get_ai_response,
    detect_state, detect_intent, STATE_URLS
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
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = data.get("question", "").strip()
    state_code = data.get("state_code", None)

    if not user_question:
        return jsonify({"error": "Please enter a question"}), 400

    # Step 1: Detect intent — catch typos, abbreviations, out-of-scope
    intent = detect_intent(user_question)

    # Out of scope — politely redirect
    if intent["type"] == "out_of_scope":
        return jsonify({
            "answer": "I'm specialized in U.S. health insurance benefits — Medicaid, ACA Marketplace, and CHIP. I'm not able to help with that topic, but I'd be happy to answer any questions about health coverage eligibility!",
            "sources": [],
            "show_state_picker": False,
            "clarification": None
        })

    # Abbreviation or fuzzy match — ask for confirmation
    if intent["type"] in ["abbreviation", "fuzzy"] and intent.get("clarification"):
        return jsonify({
            "answer": None,
            "sources": [],
            "show_state_picker": False,
            "clarification": {
                "message": f"Did you mean information about {intent['clarification']}?",
                "expanded_query": intent["expanded_query"],
                "label": intent["clarification"]
            }
        })

    # Step 2: Detect state if not explicitly passed
    if not state_code:
        state_code = detect_state(user_question)

    conversation_history = session.get("conversation_history", [])
    answer, sources = get_ai_response(
        user_question, conversation_history, knowledge_base, state_code=state_code
    )

    conversation_history.append({"role": "user", "content": user_question})
    conversation_history.append({"role": "assistant", "content": answer})
    session["conversation_history"] = conversation_history[-20:]
    session["last_topic"] = user_question

    return jsonify({
        "answer": answer,
        "sources": sources,
        "show_state_picker": state_code is None,
        "detected_state": state_code,
        "clarification": None
    })

@app.route("/ask-state", methods=["POST"])
def ask_state():
    data = request.get_json()
    state_code = data.get("state_code", "").strip().upper()

    # Handle full state names typed by user
    if len(state_code) > 2:
        from eligibility_engine import STATE_NAME_TO_CODE
        state_code = STATE_NAME_TO_CODE.get(state_code.lower(), state_code[:2])

    last_topic = session.get("last_topic", "Medicaid eligibility rules")
    conversation_history = session.get("conversation_history", [])

    if state_code not in STATE_URLS:
        return jsonify({"error": f"Sorry, I don't recognize '{state_code}' as a U.S. state. Try using the 2-letter code like CA or NY."}), 400

    state_name = STATE_URLS[state_code]["name"]
    question = f"What are the Medicaid eligibility rules specific to {state_name}? The user was asking about: {last_topic}"

    answer, sources = get_ai_response(
        question, conversation_history, knowledge_base, state_code=state_code
    )

    conversation_history.append({"role": "user", "content": f"Tell me about {state_name}"})
    conversation_history.append({"role": "assistant", "content": answer})
    session["conversation_history"] = conversation_history[-20:]

    return jsonify({
        "answer": answer,
        "sources": sources,
        "state_name": state_name
    })

@app.route("/reset", methods=["POST"])
def reset():
    session["conversation_history"] = []
    session["last_topic"] = ""
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)