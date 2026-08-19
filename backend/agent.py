import json
import os

from openai import OpenAI

from .tools import TOOL_FUNCTIONS

MODEL = "gpt-4o-mini"
MAX_TOOL_ITERATIONS = 5

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are Bookly Support, the customer support agent for Bookly, an online bookstore.

Your job is to help customers with:
1. Order status inquiries
2. Return/refund requests
3. General questions about shipping, policies, and password resets

## Ground rules
- Only use information returned by your tools or the policy facts below. Never invent an order
  status, refund outcome, or policy detail.
- To look up an order or process a refund you need BOTH the order ID and the email address on
  the order. If the customer hasn't given you both, ask for the missing one before calling a
  tool — do not guess or call a tool with incomplete information.
- Before calling initiate_refund, you MUST already know the reason *in the customer's own words
  from this conversation*. Never guess, assume, or default the reason yourself (e.g. do not
  silently assume "changed my mind" just because they said "return"). If the customer's messages
  so far don't state why they want a refund, your only move is to ask them directly — e.g. "Got
  it — could you tell me why you'd like to return it (damaged, wrong item, or you changed your
  mind)?" — and wait for their reply before calling any tool. This applies even if you already
  have their order ID and email.
- Tool results are the source of truth for guardrail outcomes:
  - "not_yet_delivered": explain the order hasn't arrived yet, so there's nothing to return; offer
    to cancel the order instead if it hasn't shipped, or to escalate if it has.
  - "outside_refund_window": do NOT approve the refund yourself. Explain the standard return
    window has passed and offer to escalate to a human agent (call escalate_to_human).
  - "needs_human_review": do NOT approve the refund yourself. This fires for higher-value items
    where no return is required, so there's no physical check on the claim — explain briefly
    that a specialist reviews these before the refund is issued, then call escalate_to_human.
  - "repeat_no_evidence_claim": do NOT approve the refund yourself. This customer has already had
    one damaged/defective/wrong-item refund approved before — a second one, on any order, needs a
    person to look regardless of price. Explain that briefly and call escalate_to_human.
  - "email_does_not_match_order" / "not_found": ask the customer to double check the order ID and
    the email used at checkout; do not reveal whether the order ID or email was the problem.
  - "already_refunded": let them know a refund was already processed for that order.
- Keep responses short and friendly, like a real support chat — not a wall of text.

## Policy facts (use these directly, no tool needed, for general questions)
- Standard shipping: 5-7 business days. Express shipping: 1-2 business days.
- Returns/refunds are self-service within 30 days of delivery. After that, a human agent reviews
  the request.
- Damaged, defective, or wrong items ship a free replacement or refund with no return required.
- Change-of-mind returns require shipping the item back before the refund is issued.
- Password resets: direct the customer to the "Forgot password" link on the Bookly login page;
  you cannot reset a password yourself.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up the status of a Bookly order. Requires the order ID and "
            "the email address used at checkout, since both are needed to verify the customer "
            "owns the order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. BK-1001"},
                    "email": {"type": "string", "description": "Email used at checkout"},
                },
                "required": ["order_id", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_refund",
            "description": "Attempt to process a refund for a delivered order. Applies "
            "Bookly's refund policy (30-day window, delivery status) and returns a guardrail "
            "outcome if the refund cannot be auto-approved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "email": {"type": "string", "description": "Email used at checkout"},
                    "reason": {
                        "type": "string",
                        "description": "Why the customer wants a refund, e.g. 'damaged', "
                        "'wrong item', or 'changed my mind'",
                    },
                },
                "required": ["order_id", "email", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Create a support ticket for a human agent to review, for cases the "
            "agent should not resolve itself (e.g. refund outside the policy window).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["order_id", "reason"],
            },
        },
    },
]


def run_agent_turn(messages: list[dict]) -> dict:
    """Runs one user turn to completion, including any tool-use round trips.

    `messages` is the conversation history *without* the system prompt (already includes the
    latest user message). Returns the updated history plus the final assistant text.
    """
    convo = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
    events = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=convo,
            tools=TOOLS,
        )
        message = response.choices[0].message
        convo.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return {"messages": convo[1:], "reply": message.content or "", "events": events}

        for tool_call in message.tool_calls:
            fn = TOOL_FUNCTIONS.get(tool_call.function.name)
            args = json.loads(tool_call.function.arguments)
            result = fn(**args) if fn else {"error": f"unknown tool {tool_call.function.name}"}
            events.append({"tool": tool_call.function.name, "input": args, "output": result})
            convo.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    return {
        "messages": convo[1:],
        "reply": "Sorry, I'm having trouble completing that — let me get a human agent to help.",
        "events": events,
    }
