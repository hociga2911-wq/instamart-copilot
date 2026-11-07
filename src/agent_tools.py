

"""Part D: SQLite, RAG and refund tools for the ReAct agent."""

from pathlib import Path
from datetime import datetime, timezone
import json
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "instamart.db"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LEDGER_PATH = OUTPUT_DIR / "refund_ledger.jsonl"

SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rag_policy import retrieve


def get_order(order_id):
    """Look up an order in SQLite."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT order_id, status, order_amount, delivery_minutes
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

    if row is None:
        return {"error": f"Order {order_id} was not found."}

    delivery = row["delivery_minutes"]

    return {
        "order_id": row["order_id"],
        "status": row["status"],
        "order_amount": float(row["order_amount"]),
        "delivery_minutes": (
            float(delivery) if delivery is not None else None
        )
    }


def search_policy(query):
    """Retrieve the three most relevant policy chunks."""
    results = retrieve(query, k=3)

    return {
        "query": query,
        "results": [
            {
                "source": item["source"],
                "text": item["text"],
                "score": item["score"]
            }
            for item in results
        ]
    }


def calculate_refund(order_amount, delivery_minutes):
    """Calculate the late-delivery refund amount.

    The agent must first verify that the order is completed.
    """
    try:
        amount = float(order_amount)
        minutes = float(delivery_minutes)
    except (TypeError, ValueError):
        return {
            "error": "A valid order amount and delivery time are required."
        }

    if amount < 0 or minutes < 0:
        return {
            "error": "Order amount and delivery time must be non-negative."
        }

    refund = amount if minutes > 45 else 0.0

    return {
        "refund_inr": round(refund, 2),
        "eligible": refund > 0,
        "reason": (
            "Completed order delivered more than 45 minutes."
            if refund > 0
            else "Delivery was within 45 minutes."
        )
    }


def _append_ledger(tool_name, order_id, refund_inr):
    """Append a refund or escalation event to the JSONL ledger."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "order_id": order_id,
        "refund_inr": round(float(refund_inr), 2)
    }

    with LEDGER_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    return record


def issue_refund(order_id, refund_inr):
    """Record an automatically approved refund up to INR 1000."""
    try:
        amount = float(refund_inr)
    except (TypeError, ValueError):
        return {"error": "Invalid refund amount."}

    if amount <= 0:
        return {"error": "Refund amount must be greater than zero."}

    if amount > 1000:
        return {
            "error": "Refund above INR 1000 requires human approval."
        }

    record = _append_ledger("issue_refund", order_id, amount)

    return {
        "status": "issued",
        "order_id": order_id,
        "refund_inr": amount,
        "ledger_timestamp": record["timestamp"]
    }


def escalate_to_human(order_id, refund_inr):
    """Record a refund requiring human approval."""
    try:
        amount = float(refund_inr)
    except (TypeError, ValueError):
        return {"error": "Invalid refund amount."}

    if amount <= 1000:
        return {
            "error": "Only refunds above INR 1000 require escalation."
        }

    record = _append_ledger("escalate_to_human", order_id, amount)

    return {
        "status": "escalated",
        "order_id": order_id,
        "refund_inr": amount,
        "message": "Sent to a human support lead for approval.",
        "ledger_timestamp": record["timestamp"]
    }


TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up an order by its order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Retrieve relevant policy document chunks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_refund",
            "description": "Calculate late-delivery refund eligibility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_amount": {"type": "number"},
                    "delivery_minutes": {"type": "number"}
                },
                "required": ["order_amount", "delivery_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Record an automatically approved refund up to INR 1000.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "refund_inr": {"type": "number"}
                },
                "required": ["order_id", "refund_inr"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Send a refund above INR 1000 to a human support lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "refund_inr": {"type": "number"}
                },
                "required": ["order_id", "refund_inr"]
            }
        }
    }
]


TOOL_MAP = {
    "get_order": get_order,
    "search_policy": search_policy,
    "calculate_refund": calculate_refund,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human
}


def execute_tool(tool_name, arguments):
    """Validate the tool name and execute it with parsed arguments."""
    function = TOOL_MAP.get(tool_name)

    if function is None:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return function(**arguments)
    except (TypeError, ValueError) as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    print("Available tools:", list(TOOL_MAP))

    print("\nTesting an existing order:")
    print(json.dumps(get_order("ORD-110093"), indent=2))

    print("\nTesting a cancelled order:")
    print(json.dumps(get_order("ORD-107264"), indent=2))

    print("\nTesting a nonexistent order:")
    print(json.dumps(get_order("ORD-999999"), indent=2))

    print("\nTesting refund calculation:")
    print(json.dumps(calculate_refund(127.50, 46), indent=2))

    print("\nTesting policy search:")
    print(json.dumps(
        search_policy("refund policy late delivery"), indent=2
    ))

    print("\nLedger path:", LEDGER_PATH)
    print("Smoke tests do not issue refunds or write ledger entries.")
