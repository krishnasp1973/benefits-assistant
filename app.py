from flask import Flask, render_template, request, jsonify, session
import os
from eligibility_engine import load_knowledge_base, get_ai_response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")
knowledge_base = load_knowledge_base()

@app.route("/")
def index():
    session["conversation_history"] = []
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = data.get("question", "").strip()
   
    if not user_question:
        return jsonify({"error": "Please enter a question"}), 400
   
    conversation_history = session.get("conversation_history", [])
   
    # Now returns both answer and sources
    answer, sources = get_ai_response(user_question, conversation_history, knowledge_base)
   
    conversation_history.append({"role": "user", "content": user_question})
    conversation_history.append({"role": "assistant", "content": answer})
    session["conversation_history"] = conversation_history[-20:]
   
    return jsonify({"answer": answer, "sources": sources})

@app.route("/reset", methods=["POST"])
def reset():
    session["conversation_history"] = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)