import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load your API key from the .env file
load_dotenv()

# Create the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_knowledge_base():
    """
    Reads our rules.json file and returns it as a Python dictionary.
    This is our 'knowledge base' — the ground truth the AI will reason over.
    """
    rules_path = os.path.join(os.path.dirname(__file__), "data", "rules.json")
    with open(rules_path, "r") as f:
        return json.load(f)

def build_system_prompt(knowledge_base):
    """
    Converts the knowledge base into a clear system prompt.
   
    The system prompt is like 'instructions given to the AI before the conversation starts.'
    We're telling it: here are the rules, answer questions based only on these.
    """
    kb_text = json.dumps(knowledge_base, indent=2)
   
    system_prompt = f"""You are a Benefits Eligibility Assistant specializing in U.S. health insurance programs.
Your role is to help users understand whether they may qualify for Medicaid, ACA Marketplace plans, or CHIP (Children's Health Insurance Program).

You have access to the following eligibility knowledge base:

{kb_text}

INSTRUCTIONS:
1. Answer questions clearly and in plain English — avoid jargon
2. Always base your answers on the knowledge base provided above
3. When discussing income limits, be specific and cite the numbers from the knowledge base
4. If a user shares their income or family size, help them understand which programs they may qualify for
5. Always recommend users confirm eligibility with their state agency or healthcare.gov, since rules can vary by state
6. Be empathetic — people asking about benefits may be in difficult situations
7. If you're unsure about something not in the knowledge base, say so clearly rather than guessing
8. Keep answers concise but complete — aim for 3-5 sentences unless more detail is needed

Remember: You are providing general educational information, not legal or medical advice."""

    return system_prompt

def get_ai_response(user_question, conversation_history, knowledge_base):
    """
    Sends the user's question to GPT-4 and gets a response.
   
    Parameters:
    - user_question: what the user just typed
    - conversation_history: list of previous messages (so the AI remembers context)
    - knowledge_base: the rules dictionary loaded from rules.json
   
    Returns: the AI's answer as a string
    """
   
    # Build the full list of messages to send to the API
    # This includes: system prompt + all previous messages + the new question
    messages = [
        {"role": "system", "content": build_system_prompt(knowledge_base)}
    ]
   
    # Add conversation history (so the AI remembers earlier messages)
    messages.extend(conversation_history)
   
    # Add the new question
    messages.append({"role": "user", "content": user_question})
   
    # Call the OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # Cost-effective; upgrade to gpt-4o for better answers
        messages=messages,
        temperature=0.3,       # Lower = more factual/consistent; higher = more creative
        max_tokens=500         # Limit response length
    )
   
    # Extract just the text from the response
    return response.choices[0].message.content

def run_terminal_demo():
    """
    A simple command-line demo so you can test the AI without a web browser.
    Type your questions directly in the terminal.
    """
    print("\n" + "="*60)
    print("  Benefits Eligibility Assistant")
    print("  Type 'quit' to exit")
    print("="*60 + "\n")
   
    knowledge_base = load_knowledge_base()
    conversation_history = []
   
    while True:
        # Get user input
        user_input = input("You: ").strip()
       
        # Check if they want to quit
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
       
        # Skip empty input
        if not user_input:
            continue
       
        print("Assistant: Thinking...", end="\r")
       
        # Get the AI's answer
        answer = get_ai_response(user_input, conversation_history, knowledge_base)
       
        # Print the answer
        print(f"Assistant: {answer}\n")
       
        # Save this exchange to conversation history
        # This is how the AI "remembers" what was said earlier
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": answer})

# This block runs only when you execute this file directly
# (not when it's imported by app.py)
if __name__ == "__main__":
    run_terminal_demo()