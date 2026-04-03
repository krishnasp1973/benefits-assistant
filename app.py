from flask import Flask, render_template, request, jsonify, session
import os
from eligibility_engine import load_knowledge_base, get_ai_response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Secret key needed for Flask sessions (stores conversation history per user)
# In production you'd use a long random string; this is fine for development
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

# Load the knowledge base once when the server starts (more efficient than loading per request)
knowledge_base = load_knowledge_base()

@app.route("/")
def index():
    """Serve the main chat page"""
    # Clear conversation history when user loads/refreshes the page
    session["conversation_history"] = []
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    """
    API endpoint that receives a question from the browser and returns an AI answer.
   
    The browser sends: { "question": "Do I qualify for Medicaid?" }
    This function returns: { "answer": "Based on your information..." }
    """
    data = request.get_json()
    user_question = data.get("question", "").strip()
   
    if not user_question:
        return jsonify({"error": "Please enter a question"}), 400
   
    # Retrieve the conversation history from the session
    conversation_history = session.get("conversation_history", [])
   
    # Get the AI's answer
    answer = get_ai_response(user_question, conversation_history, knowledge_base)
   
    # Update conversation history
    conversation_history.append({"role": "user", "content": user_question})
    conversation_history.append({"role": "assistant", "content": answer})
   
    # Save updated history back to the session
    # Limit to last 10 exchanges to avoid very long prompts
    session["conversation_history"] = conversation_history[-20:]
   
    return jsonify({"answer": answer})

@app.route("/reset", methods=["POST"])
def reset():
    """Clears the conversation history so users can start fresh"""
    session["conversation_history"] = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    # debug=True means the server auto-restarts when you save changes
    # Never use debug=True in production!
    app.run(debug=True, port=5000)