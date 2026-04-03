import json
import os
import re
import requests
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_knowledge_base():
    rules_path = os.path.join(os.path.dirname(__file__), "data", "rules.json")
    with open(rules_path, "r") as f:
        return json.load(f)

def fetch_page_content(url, max_chars=3000):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 30]
        clean_text = '\n'.join(lines)
        return clean_text[:max_chars]
    except Exception as e:
        print(f"Could not fetch {url}: {e}")
        return None

def identify_relevant_urls(question, knowledge_base):
    question_lower = question.lower()
    source_urls = knowledge_base.get("source_urls", {})
    matched_categories = set()

    keyword_map = {
        "community": ["community_engagement", "new_york"],
        "engagement": ["community_engagement", "new_york"],
        "requirement": ["community_engagement", "new_york"],
        "work rule": ["community_engagement", "new_york"],
        "2027": ["community_engagement", "new_york"],
        "new york": ["new_york"],
        "ny ": ["new_york"],
        "nys": ["new_york"],
        "stay covered": ["new_york", "community_engagement"],
        "nystateofhealth": ["new_york", "community_engagement"],
        "chip": ["chip"],
        "children": ["chip"],
        "child": ["chip"],
        "kids": ["chip"],
        "pregnant": ["pregnancy"],
        "pregnancy": ["pregnancy"],
        "job loss": ["job_loss"],
        "lost job": ["job_loss"],
        "lost my job": ["job_loss"],
        "unemployed": ["job_loss"],
        "laid off": ["job_loss"],
        "open enrollment": ["open_enrollment"],
        "enrollment period": ["open_enrollment"],
        "deadline": ["open_enrollment"],
        "marketplace": ["aca_marketplace"],
        "aca": ["aca_marketplace"],
        "subsid": ["aca_marketplace"],
        "premium": ["aca_marketplace"],
        "tax credit": ["aca_marketplace"],
    }

    for keyword, categories in keyword_map.items():
        if keyword in question_lower:
            for cat in categories:
                matched_categories.add(cat)

    if not matched_categories:
        matched_categories.add("general_eligibility")

    seen = set()
    urls = []
    for category in matched_categories:
        for url in source_urls.get(category, []):
            if url not in seen:
                seen.add(url)
                urls.append(url)

    return urls[:3]

def build_system_prompt(knowledge_base, page_contents):
    kb_text = json.dumps(knowledge_base, indent=2)

    pages_section = ""
    if page_contents:
        pages_section = "\n\nLIVE PAGE CONTENT (fetched from official government sources):\n"
        for url, content in page_contents.items():
            pages_section += f"\n--- FROM: {url} ---\n{content}\n"

    return f"""You are a Benefits Eligibility Assistant specializing in U.S. health insurance programs.
Your role is to help users understand eligibility for Medicaid, ACA Marketplace plans, and CHIP.

KNOWLEDGE BASE:
{kb_text}
{pages_section}

INSTRUCTIONS:
1. PRIORITIZE the LIVE PAGE CONTENT over everything else when available
2. Be specific and detailed — quote actual requirements, dates, deadlines, and rules from the live content
3. If the live page mentions specific steps or requirements, list them clearly
4. Answer in plain English but include all specific details
5. At the end of EVERY answer include a Sources section like this:
   Sources:
   - https://example.gov/page
6. Always recommend users verify with their state agency
7. Be empathetic

Remember: General educational information only, not legal or medical advice."""

def get_ai_response(user_question, conversation_history, knowledge_base):
    relevant_urls = identify_relevant_urls(user_question, knowledge_base)
    print(f"\nFetching {len(relevant_urls)} pages for: {user_question[:60]}")

    page_contents = {}
    for url in relevant_urls:
        content = fetch_page_content(url)
        if content:
            page_contents[url] = content
            print(f"  Got {len(content)} chars from {url}")
        else:
            print(f"  Failed: {url}")

    messages = [
        {"role": "system", "content": build_system_prompt(knowledge_base, page_contents)}
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800
    )

    full_text = response.choices[0].message.content or ""
    sources = extract_sources(full_text, list(page_contents.keys()))
    clean_answer = clean_answer_text(full_text)

    return clean_answer, sources

def extract_sources(text, fetched_urls=None):
    sources = []
    seen = set()

    if fetched_urls:
        for url in fetched_urls:
            if url not in seen:
                seen.add(url)
                label = url.split('//')[1].split('/')[0].replace('www.', '')
                sources.append({"url": url, "label": label})

    url_pattern = r'https?://[^\s\)\]\,\>\"\'<]+'
    for url in re.findall(url_pattern, text):
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
    print("  Benefits Eligibility Assistant with RAG")
    print("  Type quit to exit")
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

        print("Fetching pages and thinking...")
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