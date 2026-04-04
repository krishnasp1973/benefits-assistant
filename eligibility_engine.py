import json
import os
import re
import requests
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── All 50 states ──
STATE_URLS = {
    "AL": {"name": "Alabama",       "url": "https://medicaid.alabama.gov/"},
    "AK": {"name": "Alaska",        "url": "https://health.alaska.gov/dsds/Pages/medicaid/default.aspx"},
    "AZ": {"name": "Arizona",       "url": "https://www.healthearizonaplus.gov/"},
    "AR": {"name": "Arkansas",      "url": "https://www.medicaid.state.ar.us/"},
    "CA": {"name": "California",    "url": "https://www.dhcs.ca.gov/services/medi-cal/Pages/default.aspx"},
    "CO": {"name": "Colorado",      "url": "https://hcpf.colorado.gov/health-first-colorado"},
    "CT": {"name": "Connecticut",   "url": "https://www.ct.gov/dss/cwp/view.asp?a=2353&q=305172"},
    "DE": {"name": "Delaware",      "url": "https://medicaid.dhss.delaware.gov/"},
    "FL": {"name": "Florida",       "url": "https://www.flmedicaidmanagedcare.com/"},
    "GA": {"name": "Georgia",       "url": "https://medicaid.georgia.gov/"},
    "HI": {"name": "Hawaii",        "url": "https://medquest.hawaii.gov/"},
    "ID": {"name": "Idaho",         "url": "https://healthandwelfare.idaho.gov/services-programs/medicaid"},
    "IL": {"name": "Illinois",      "url": "https://hfs.illinois.gov/medicaid"},
    "IN": {"name": "Indiana",       "url": "https://www.in.gov/medicaid/"},
    "IA": {"name": "Iowa",          "url": "https://hhs.iowa.gov/programs/programs-and-services/medicaid"},
    "KS": {"name": "Kansas",        "url": "https://www.kancare.ks.gov/"},
    "KY": {"name": "Kentucky",      "url": "https://chfs.ky.gov/agencies/dms/Pages/default.aspx"},
    "LA": {"name": "Louisiana",     "url": "https://ldh.la.gov/medicaid"},
    "ME": {"name": "Maine",         "url": "https://www.maine.gov/dhhs/ofi/programs-services/mainecare"},
    "MD": {"name": "Maryland",      "url": "https://mmcp.health.maryland.gov/"},
    "MA": {"name": "Massachusetts", "url": "https://www.mass.gov/masshealth"},
    "MI": {"name": "Michigan",      "url": "https://www.michigan.gov/mdhhs/adult-child-serv/medicaid"},
    "MN": {"name": "Minnesota",     "url": "https://mn.gov/dhs/people-we-serve/adults/health-care/health-care-programs/programs-and-services/medical-assistance.jsp"},
    "MS": {"name": "Mississippi",   "url": "https://medicaid.ms.gov/"},
    "MO": {"name": "Missouri",      "url": "https://dss.mo.gov/mhd/"},
    "MT": {"name": "Montana",       "url": "https://dphhs.mt.gov/MontanaHealthcarePrograms/Medicaid"},
    "NE": {"name": "Nebraska",      "url": "https://dhhs.ne.gov/Pages/Medicaid.aspx"},
    "NV": {"name": "Nevada",        "url": "https://dhcfp.nv.gov/"},
    "NH": {"name": "New Hampshire", "url": "https://www.dhhs.nh.gov/programs-services/medicaid"},
    "NJ": {"name": "New Jersey",    "url": "https://www.state.nj.us/humanservices/dmahs/home/"},
    "NM": {"name": "New Mexico",    "url": "https://www.hsd.state.nm.us/LookingForAssistance/medicaid.aspx"},
    "NY": {"name": "New York",      "url": "https://www.health.ny.gov/health_care/medicaid/"},
    "NC": {"name": "North Carolina","url": "https://medicaid.ncdhhs.gov/"},
    "ND": {"name": "North Dakota",  "url": "https://www.hhs.nd.gov/healthcare/medicaid"},
    "OH": {"name": "Ohio",          "url": "https://medicaid.ohio.gov/"},
    "OK": {"name": "Oklahoma",      "url": "https://oklahoma.gov/ohca.html"},
    "OR": {"name": "Oregon",        "url": "https://www.oregon.gov/oha/hsd/ohp/pages/index.aspx"},
    "PA": {"name": "Pennsylvania",  "url": "https://www.dhs.pa.gov/Services/Assistance/Pages/MA-General-Info.aspx"},
    "RI": {"name": "Rhode Island",  "url": "https://eohhs.ri.gov/programs-and-services/adults/medicaid"},
    "SC": {"name": "South Carolina","url": "https://www.scdhhs.gov/"},
    "SD": {"name": "South Dakota",  "url": "https://dss.sd.gov/medicaid/"},
    "TN": {"name": "Tennessee",     "url": "https://www.tn.gov/tenncare.html"},
    "TX": {"name": "Texas",         "url": "https://www.hhs.texas.gov/services/health/medicaid-chip"},
    "UT": {"name": "Utah",          "url": "https://medicaid.utah.gov/"},
    "VT": {"name": "Vermont",       "url": "https://dvha.vermont.gov/"},
    "VA": {"name": "Virginia",      "url": "https://www.dmas.virginia.gov/"},
    "WA": {"name": "Washington",    "url": "https://www.hca.wa.gov/apple-health"},
    "WV": {"name": "West Virginia", "url": "https://dhhr.wv.gov/bms/Pages/default.aspx"},
    "WI": {"name": "Wisconsin",     "url": "https://www.dhs.wisconsin.gov/medicaid/index.htm"},
    "WY": {"name": "Wyoming",       "url": "https://health.wyo.gov/healthcarefin/medicaid/"},
    "DC": {"name": "Washington DC", "url": "https://dhcf.dc.gov/"},
}

# ── Topic abbreviations and typo mappings ──
TOPIC_SHORTCUTS = {
    "ce":   {"match": "community engagement", "label": "Community Engagement Requirements"},
    "oe":   {"match": "open enrollment",      "label": "Open Enrollment"},
    "mc":   {"match": "medicaid",             "label": "Medicaid"},
    "aca":  {"match": "aca marketplace",      "label": "ACA Marketplace"},
    "mkt":  {"match": "aca marketplace",      "label": "ACA Marketplace"},
    "fp":   {"match": "federal poverty level","label": "Federal Poverty Level"},
    "fpl":  {"match": "federal poverty level","label": "Federal Poverty Level"},
    "ptc":  {"match": "premium tax credit",   "label": "Premium Tax Credit"},
    "csr":  {"match": "cost sharing reduction","label": "Cost Sharing Reduction"},
    "chip": {"match": "chip children",        "label": "CHIP — Children's Health"},
}

# ── Fuzzy topic matching for typos ──
KNOWN_TOPICS = {
    "community engagement": "Community Engagement Requirements",
    "open enrollment": "Open Enrollment Deadlines",
    "medicaid": "Medicaid Eligibility",
    "marketplace": "ACA Marketplace",
    "premium tax credit": "Premium Tax Credits",
    "chip": "CHIP — Children's Coverage",
    "federal poverty level": "Federal Poverty Level",
    "pregnancy": "Pregnancy Coverage",
    "job loss": "Coverage After Job Loss",
    "income limit": "Income Limits",
    "cost sharing": "Cost Sharing Reductions",
}

STATE_NAME_TO_CODE = {}
for code, info in STATE_URLS.items():
    STATE_NAME_TO_CODE[info["name"].lower()] = code
    STATE_NAME_TO_CODE[code.lower()] = code

def load_knowledge_base():
    rules_path = os.path.join(os.path.dirname(__file__), "data", "rules.json")
    with open(rules_path, "r") as f:
        return json.load(f)

def fetch_page_content(url, max_chars=3000):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 30]
        return '\n'.join(lines)[:max_chars]
    except Exception as e:
        print(f"Could not fetch {url}: {e}")
        return None

def detect_state(text):
    text_lower = text.lower().strip()
    if text_lower.upper() in STATE_URLS:
        return text_lower.upper()
    if text_lower in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[text_lower]
    for name, code in STATE_NAME_TO_CODE.items():
        if len(name) > 2 and name in text_lower:
            return code
    return None

def levenshtein(s1, s2):
    """Calculates edit distance between two strings for fuzzy matching."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(c1 != c2)))
        prev = curr
    return prev[-1]

def detect_intent(question):
    """
    Analyzes the user's question and returns:
    - clarification: a suggested correction if the query is ambiguous or abbreviated
    - topic: the detected topic if clear
    - is_out_of_scope: True if the question is not about benefits
    """
    q = question.lower().strip()
    words = q.split()

    # Check for known abbreviations/shortcuts
    for word in words:
        if word in TOPIC_SHORTCUTS:
            shortcut = TOPIC_SHORTCUTS[word]
            return {
                "clarification": shortcut["label"],
                "expanded_query": shortcut["match"],
                "type": "abbreviation"
            }

    # Check for short/ambiguous queries (less than 4 words, no clear topic)
    if len(words) <= 3:
        # Try fuzzy match against known topics
        best_match = None
        best_score = 999
        for topic in KNOWN_TOPICS:
            score = levenshtein(q, topic)
            # Also check if any word is close to a topic word
            for tw in topic.split():
                for qw in words:
                    ws = levenshtein(qw, tw)
                    if ws < score:
                        score = ws
                        best_match = topic
        if best_match and best_score < 4:
            return {
                "clarification": KNOWN_TOPICS[best_match],
                "expanded_query": best_match,
                "type": "fuzzy"
            }

    # Check if question is clearly out of scope
    out_of_scope_keywords = [
        "weather", "recipe", "sports", "movie", "song", "stock",
        "crypto", "bitcoin", "dating", "travel", "hotel", "flight",
        "restaurant", "game", "celebrity", "fashion", "shopping"
    ]
    for keyword in out_of_scope_keywords:
        if keyword in q:
            return {
                "type": "out_of_scope",
                "clarification": None,
                "expanded_query": None
            }

    return {"type": "clear", "clarification": None, "expanded_query": None}

def identify_relevant_urls(question, knowledge_base):
    question_lower = question.lower()
    source_urls = knowledge_base.get("source_urls", {})
    matched_categories = set()

    keyword_map = {
        "community": ["community_engagement", "new_york"],
        "engagement": ["community_engagement", "new_york"],
        "requirement": ["community_engagement"],
        "2027": ["community_engagement", "new_york"],
        "chip": ["chip"],
        "children": ["chip"],
        "child": ["chip"],
        "kids": ["chip"],
        "pregnant": ["pregnancy"],
        "pregnancy": ["pregnancy"],
        "job loss": ["job_loss"],
        "lost job": ["job_loss"],
        "unemployed": ["job_loss"],
        "laid off": ["job_loss"],
        "open enrollment": ["open_enrollment"],
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

    return urls[:2]

def build_system_prompt(knowledge_base, page_contents, state_code=None):
    kb_text = json.dumps(knowledge_base, indent=2)

    pages_section = ""
    if page_contents:
        pages_section = "\n\nLIVE PAGE CONTENT (fetched from official government sources):\n"
        for url, content in page_contents.items():
            pages_section += f"\n--- FROM: {url} ---\n{content}\n"

    state_instruction = ""
    if state_code and state_code in STATE_URLS:
        state_name = STATE_URLS[state_code]["name"]
        state_instruction = f"Focus your answer on {state_name}-specific rules using the live page content."

    return f"""You are a Benefits Eligibility Assistant specializing in U.S. health insurance programs.

KNOWLEDGE BASE:
{kb_text}
{pages_section}

INSTRUCTIONS:
1. PRIORITIZE LIVE PAGE CONTENT over knowledge base when available
2. Be specific — include actual dates, income thresholds, requirements from live content
3. List steps or requirements clearly when the page content contains them
4. {state_instruction}
5. End EVERY answer with a Sources section:
   Sources:
   - https://example.gov/page
6. Always recommend verifying with state agency
7. Be empathetic and clear
8. If you cannot find specific information, say so honestly

Remember: General educational information only, not legal or medical advice."""

def get_ai_response(user_question, conversation_history, knowledge_base, state_code=None):
    page_contents = {}

    if state_code and state_code in STATE_URLS:
        state_url = STATE_URLS[state_code]["url"]
        print(f"\nFetching state page: {STATE_URLS[state_code]['name']}")
        content = fetch_page_content(state_url)
        if content:
            page_contents[state_url] = content
    else:
        relevant_urls = identify_relevant_urls(user_question, knowledge_base)
        print(f"\nFetching {len(relevant_urls)} pages")
        for url in relevant_urls:
            content = fetch_page_content(url)
            if content:
                page_contents[url] = content

    messages = [
        {"role": "system", "content": build_system_prompt(knowledge_base, page_contents, state_code)}
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=900
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