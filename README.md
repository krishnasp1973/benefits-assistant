\# Benefits Eligibility Assistant



An AI-powered Q\&A agent that helps users understand their eligibility for U.S. health insurance programs — Medicaid, ACA Marketplace plans, and CHIP.



\## What it does

\- Answers natural-language questions about health insurance eligibility

\- Grounds responses in structured eligibility rules (income limits, FPL thresholds, program details)

\- Maintains conversation context across multiple questions

\- Covers Medicaid, ACA/Marketplace subsidies, and CHIP for children



\## Tech stack

\- \*\*Python 3.11\*\* + \*\*Flask\*\* — web server and routing

\- \*\*OpenAI GPT-4o-mini\*\* — language model for Q\&A

\- \*\*JSON knowledge base\*\* — structured eligibility rules as the AI's source of truth

\- \*\*Vanilla JS\*\* — no frontend framework needed; keeps it simple and fast



\## How to run locally

1\. Clone the repo

2\. Create a `.env` file with your `OPENAI\_API\_KEY=...`

3\. `pip install openai flask python-dotenv`

4\. `python app.py`

5\. Open `http://localhost:5000`



\## Why I built this

This project demonstrates the intersection of healthcare/benefits domain knowledge and AI product development — using an LLM not as a black box, but grounded in a structured knowledge base to produce reliable, auditable answers.

