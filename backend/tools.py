import json
import random
import string
from datetime import date, datetime
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "orders.json"
REFUND_WINDOW_DAYS = 30
NO_EVIDENCE_REASONS = {"damaged", "defective", "wrong item"}
# Above this, a "no return needed" refund (damaged/defective/wrong item) is based purely on the
# customer's word — nothing gets physically inspected. Route those to a human instead of letting
# the agent auto-approve on an unverified claim.
HIGH_VALUE_REVIEW_THRESHOLD = 30.00


def _load_orders() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def _save_orders(orders: dict) -> None:
    with open(DATA_PATH, "w") as f:
        json.dump(orders, f, indent=2)


def _has_prior_no_evidence_refund(orders: dict, email: str, exclude_key: str) -> bool:
    email = email.strip().lower()
    for oid, o in orders.items():
        if oid == exclude_key:
            continue
        if o["email"].lower() == email and o.get("refund_type") == "full_refund_no_return_needed":
            return True
    return False


def get_order_status(order_id: str, email: str) -> dict:
    orders = _load_orders()
    order = orders.get(order_id.strip().upper())
    if not order:
        return {"found": False, "error": "no_order_with_that_id"}
    if order["email"].lower() != email.strip().lower():
        return {"found": False, "error": "email_does_not_match_order"}
    return {
        "found": True,
        "order_id": order_id.strip().upper(),
        "item": order["item"],
        "status": order["status"],
        "order_date": order["order_date"],
        "delivered_date": order["delivered_date"],
        "refunded": order["refunded"],
    }


def initiate_refund(order_id: str, email: str, reason: str) -> dict:
    orders = _load_orders()
    key = order_id.strip().upper()
    order = orders.get(key)

    if not order:
        return {"outcome": "not_found"}
    if order["email"].lower() != email.strip().lower():
        return {"outcome": "email_does_not_match_order"}
    if order["refunded"]:
        return {"outcome": "already_refunded"}
    if order["status"] != "delivered":
        # Guardrail: nothing to return before delivery — offer cancellation instead.
        return {"outcome": "not_yet_delivered", "current_status": order["status"]}

    delivered = datetime.strptime(order["delivered_date"], "%Y-%m-%d").date()
    days_since_delivery = (date.today() - delivered).days

    if days_since_delivery > REFUND_WINDOW_DAYS:
        # Guardrail: outside the self-serve window — do not auto-approve, escalate instead.
        return {
            "outcome": "outside_refund_window",
            "days_since_delivery": days_since_delivery,
            "window_days": REFUND_WINDOW_DAYS,
        }

    reason_key = reason.strip().lower()

    if reason_key in NO_EVIDENCE_REASONS:
        refund_type = "full_refund_no_return_needed"
        if _has_prior_no_evidence_refund(orders, order["email"], exclude_key=key):
            # Guardrail: a no-evidence refund is a one-time pass, not a per-order allowance —
            # otherwise the $30 ceiling is trivially dodged by splitting one claim into several.
            return {"outcome": "repeat_no_evidence_claim"}
        if order["price"] > HIGH_VALUE_REVIEW_THRESHOLD:
            # Guardrail: no return means no physical check on the claim. Above the threshold,
            # that's too much money to move on an unverified "it was damaged" alone.
            return {
                "outcome": "needs_human_review",
                "price": order["price"],
                "threshold": HIGH_VALUE_REVIEW_THRESHOLD,
            }
    else:
        refund_type = "full_refund_after_return_shipped"

    order["refunded"] = True
    order["refund_type"] = refund_type
    orders[key] = order
    _save_orders(orders)

    refund_id = "RF-" + "".join(random.choices(string.digits, k=6))
    return {
        "outcome": "approved",
        "refund_id": refund_id,
        "refund_type": refund_type,
    }


def escalate_to_human(order_id: str, reason: str) -> dict:
    ticket_id = "TCK-" + "".join(random.choices(string.digits, k=6))
    return {
        "outcome": "escalated",
        "ticket_id": ticket_id,
        "message": "A human support agent will follow up within 1 business day.",
    }


TOOL_FUNCTIONS = {
    "get_order_status": get_order_status,
    "initiate_refund": initiate_refund,
    "escalate_to_human": escalate_to_human,
}
