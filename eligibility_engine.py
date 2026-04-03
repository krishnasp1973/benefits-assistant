import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_knowledge_base():
    rules_path = os.path.join(os.path.dirname(__file__), "data", "rules.json")
    with open(rules_path, "r") as f:
        return json.load(f)

def build_system_prompt(knowledge_base):
    kb_text = json.dumps(knowledge_base, indent=2)
    return f"""You are a Benefits Eligibility Assistant specializing in U.S. health insurance programs.
Your role is to help users understand whether they may qualify for Medicaid, ACA Marketplace plans, or CHIP.

You have access to the following eligibility knowledge base:
{kb_text}

INSTRUCTIONS:
1. Answer questions clearly in plain English
2. Base answers on the knowledge base above
3. When discussing income limits, cite specific numbers
4. At the end of every answer, include a "Sources:" section with 2-3 relevant official URLs from:
   - healthcare.gov
   - medicaid.gov
   - insurekidsnow.gov
   - State health department websites when a state is mentioned (e.g. health.ny.gov for New York)
5. Format your Sources section exactly like this example:
   Sources:
   - https://www.healthcare.gov/medicaid-chip/eligibility/
   - https://www.medicaid.gov/medicaid/eligibility/index.html
6. Always recommend users verify with their state agency
7. Be empathetic and clear
8. Keep answers to 3-5 sentences before the Sources section

Remember: General educational information only, not legal or medical advice."""

def get_ai_response(user_question, conversation_history, knowledge_base):
    messages = [
        {"role": "system", "content": build_system_prompt(knowledge_base)}
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=600
    )

    full_text = response.choices[0].message.content or ""
    sources = extract_sources(full_text)
    clean_answer = clean_answer_text(full_text)

    return clean_answer, sources

def extract_sources(text):
    sources = []
    seen = set()
    url_pattern = r'https?://[^\s\)\]\,\>\"\'<]+'
    urls = re.findall(url_pattern, text)
    for url in urls:
        url = url.rstrip('.,;:)')
        if url not in seen:
            seen.add(url)
            label = url.split('//')[1].split('/')[0].replace('www.', '')
            sources.append({"url": url, "label": label})
    return sources

def clean_answer_text(text):
    cleaned = re.sub(r'\n*Sources?:.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()

def run_terminal_demo():
    print("\n" + "="*60)
    print("  Benefits Eligibility Assistant")
    print("  Type 'quit' to exit")
    print("="*60 + "\n")

    knowledge_base = load_knowledge_base()
    conversation_history = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        if not user_input:
            continue

        print("Thinking...")
        answer, sources = get_ai_response(user_input, conversation_history, knowledge_base)
        print(f"\nAssistant: {answer}\n")

        if sources:
            print("Sources:")
            for s in sources:
                print(f"  - {s['url']}")
            print()

        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    run_terminal_demo()