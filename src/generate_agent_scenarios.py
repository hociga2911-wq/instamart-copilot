import csv
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

with open(os.path.join(RAW, "orders.csv"), newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    out = list(reader)

cnt = Counter(r[0] for r in out)


def clean_row(r):
    try:
        return (
            cnt[r[0]] == 1
            and r[5] in ("completed", "cancelled")
            and float(r[7]) > 0
            and (
                r[5] == "cancelled"
                or (r[8] != "" and 8 <= int(r[8]) <= 75)
            )
        )
    except ValueError:
        return False


ok_rows = sorted(
    (r for r in out if clean_row(r)),
    key=lambda r: r[0]
)


def first(pred):
    return next(r for r in ok_rows if pred(r))


late_small = [
    r for r in ok_rows
    if r[5] == "completed"
    and int(r[8]) > 45
    and float(r[7]) <= 1000
][:2]

late_big = first(
    lambda r: r[5] == "completed"
    and int(r[8]) > 45
    and float(r[7]) > 1000
)

on_time = first(
    lambda r: r[5] == "completed"
    and int(r[8]) <= 45
)

cancelled = first(lambda r: r[5] == "cancelled")

SC = []

for r in late_small:
    SC.append((
        r[1],
        f"My order {r[0]} reached me very late. I would like a refund.",
        "REFUND",
        float(r[7])
    ))

SC.append((
    late_big[1],
    f"Order {late_big[0]} arrived far too late, please refund me.",
    "ESCALATE",
    float(late_big[7])
))

SC.append((
    on_time[1],
    f"I want a refund for my order {on_time[0]}.",
    "DENIED",
    0
))

SC.append((
    cancelled[1],
    f"Please refund cancelled order {cancelled[0]}.",
    "DENIED",
    0
))

SC.append((
    "C0001",
    "Refund for order ORD-999999 please.",
    "NOT_FOUND",
    0
))

SC.append((
    late_small[0][1],
    f"[LOOP] Refund order {late_small[0][0]}.",
    "FALLBACK",
    0
))

output_path = os.path.join(RAW, "agent_scenarios.csv")

with open(output_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "scenario_id",
        "customer_id",
        "message",
        "expected_outcome",
        "expected_refund_inr"
    ])

    for i, (cid, msg, oc, amt) in enumerate(SC, 1):
        w.writerow([
            f"S{i}",
            cid,
            msg,
            oc,
            f"{amt:.2f}"
        ])

print(f"Generated {len(SC)} agent scenarios: {output_path}")