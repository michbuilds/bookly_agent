# Bookly Support Agent

A prototype customer support agent for Bookly (a fictional online bookstore), built for the
Decagon Solutions Engineering take-home. Python/FastAPI backend calling the OpenAI API directly
with native tool/function-calling (no agent-platform abstraction); minimal HTML/JS chat frontend.

## Setup

```bash
cd bookly-support-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your OpenAI API key into .env
```

## Run

```bash
uvicorn backend.main:app --reload
```

Open http://localhost:8000

## Try it

Sample orders (mocked, in `backend/data/orders.json`):

| Order ID | Email                  | Price  | Scenario                                       |
|----------|-------------------------|-------:|-------------------------------------------------|
| BK-1001  | jane.doe@example.com    | $26.99 | Still processing (not shipped)                  |
| BK-1002  | jane.doe@example.com    | $16.99 | Shipped, not yet delivered                      |
| BK-1003  | sam.lee@example.com     | $27.99 | Delivered recently — refund-eligible             |
| BK-1004  | sam.lee@example.com     | $15.99 | Delivered >30 days ago — outside refund window   |
| BK-1005  | priya.k@example.com     | $42.99 | Delivered, already refunded                      |
| BK-1006  | jane.doe@example.com    | $89.99 | Delivered recently, high-value — needs human review |
| BK-1007  | sam.lee@example.com     | $21.99 | Delivered recently — use for the repeat-claim test below |

Things to try, mapped to the assignment's minimum requirements:

- **Multi-turn**: "I want a refund" → agent asks for order ID and email before doing anything.
- **Tool use**: "What's the status of BK-1002, jane.doe@example.com?" → calls `get_order_status`.
- **Clarifying question**: "I want to return BK-1003" → agent asks *why* (damaged vs. changed
  mind) before calling `initiate_refund`, since that changes the refund type — it never guesses
  or defaults the reason itself.
- **Guardrail / escalation (time-based)**: ask to refund BK-1004 (outside the 30-day window) —
  the agent won't auto-approve it and instead offers to escalate to a human.
- **Guardrail / escalation (value-based)**: ask to refund BK-1006 as damaged — no return is
  required for damaged items, so there's no physical check on the claim; above $30 the agent
  routes it to a human instead of trusting the customer's word, and automatically calls
  `escalate_to_human`.
- **Guardrail / escalation (repeat-claim)**: refund BK-1007 as damaged (sam.lee@example.com) —
  it's under $30 and a first claim, so it auto-approves. Then, in the same or a new conversation,
  ask to refund BK-1003 as damaged too (same customer). Even though BK-1003 is also under $30,
  the agent won't approve it — this customer already used their one no-evidence refund, so any
  further claim goes to a human regardless of price. This check reads real order history, not
  conversation memory, so it works even across separate conversations.
- **General Q&A**: "How long does shipping take?" / "How do I reset my password?" — answered
  from policy knowledge in the system prompt, no tool call needed.

## Architecture notes

- Conversation memory is held client-side: the frontend keeps the full OpenAI-format message
  history and resends it each turn; the backend is stateless per request. This was a deliberate
  simplification for a 4-hour prototype — see the pitch deck for what a production version would
  do differently (durable server-side session store, auth-bound to the customer).
- Refund guardrails (delivery status, 30-day window, high-value-with-no-return-check) are enforced
  in `backend/tools.py`, not just requested via the prompt — the tool itself refuses to
  auto-approve and returns a structured outcome the agent must relay, so the guardrail can't be
  prompt-injected away.
- Known limitation, by design: damage/defect claims are trusted on the customer's word alone (no
  photo evidence, no fraud-history check). The value threshold is a cheap mitigation for a 4-hour
  prototype, not a substitute for real evidence collection — see the pitch deck for what a
  production build would add.
