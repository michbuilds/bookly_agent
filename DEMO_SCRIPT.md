# Demo / QA Script

## Pre-flight checklist

- [ ] `.env` has a real `OPENAI_API_KEY` and is **not** committed (check `.gitignore` includes `.env`)
- [ ] `backend/data/orders.json` is reset to the clean starting state (all `refunded: false`
      except BK-1005)
- [ ] Server starts clean:
      `cd bookly-support-agent && source .venv/bin/activate && uvicorn backend.main:app --port 8000`
- [ ] Browser window is wide (>960px) — sidebar and Agent Activity panel collapse below that
- [ ] Refresh the page once before recording so History/Activity panels start empty

## Demo script (~2 min, covers all 3 minimum requirements + guardrails + general Q&A)

**1. General Q&A — no tool call needed**
> "How long does shipping take?"

Expect: direct answer from policy knowledge. Nothing appears in Agent Activity.

**2. Multi-turn + clarifying question + tool use, chained**
> "I want to return my order"

Expect: agent asks for order ID **and** email (multi-turn requirement).

> "BK-1003, sam.lee@example.com"

Expect: agent asks *why* before processing anything (clarifying-question requirement).

> "It arrived damaged"

Expect: `initiate_refund` fires (tool-use requirement), approved, no return required.

**3. Guardrail — refund outside the 30-day window**
> "I want to return order BK-1004, sam.lee@example.com, it's damaged"

Expect: order delivered >30 days ago — agent does not auto-approve, offers to escalate instead.

**4. Guardrail — high-value refund with no physical check**
> "I want to return order BK-1006, jane.doe@example.com, it arrived damaged"

Expect: no return required for damaged items, so above $30 the agent won't auto-approve on the
customer's word alone — it calls `escalate_to_human` itself. Two chained tool calls visible in
Agent Activity.

**5. Guardrail — repeat no-evidence claim (works across separate conversations)**
> "I want to return BK-1007, sam.lee@example.com, it arrived damaged"

Expect: under $30, first claim from this customer → approved instantly.

Start a **new conversation** (or just continue), then:
> "I also want to return BK-1003, sam.lee@example.com, it arrived damaged too"

Expect: even though BK-1003 is under $30, the agent won't approve — this customer already used
their one no-evidence refund. Escalates automatically. This is checked against real order
history, not conversation memory, so it holds even in a brand-new chat.

## Extra edge cases worth checking once

- **Wrong email for a real order ID** → can't verify the order, doesn't reveal which part was wrong.
- **Nonexistent order ID** → graceful "couldn't find that order" message.
- **Already-refunded order** (BK-1005, priya.k@example.com) → says a refund was already processed.
- **Refund attempt on a not-yet-delivered order** (BK-1001 or BK-1002) → explains nothing has
  arrived yet, offers cancellation instead.
- **"New conversation"** button clears the chat; the old thread's first message appears in History.
- **Quick-action cards** on the empty state send their canned prompt, same as typing it.

## After you're done testing

- [ ] Reset `backend/data/orders.json` if BK-1003/BK-1004/BK-1006/BK-1007 got mutated by testing
- [ ] Double check no API key is visible in any recording or screenshot
