import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import agent_tools
from agent import run_agent, resume_agent, SimulatedCrash

# Keep this demonstration's simulated refund separate
# from the main evaluation refund ledger.
agent_tools.LEDGER_PATH = (
    ROOT / "outputs" / "checkpoint_demo_ledger.jsonl"
)

SCENARIOS_FILE = ROOT / "data" / "raw" / "agent_scenarios.csv"

with SCENARIOS_FILE.open(
    newline="", encoding="utf-8"
) as file:
    scenarios = list(csv.DictReader(file))

s1 = next(
    scenario for scenario in scenarios
    if scenario["scenario_id"] == "S1"
)

run_id = "checkpoint_S1_demo"

print("========== SIMULATING CRASH ==========")

try:
    run_agent(
        user_message=s1["message"],
        scenario_id="S1_CHECKPOINT_DEMO",
        run_id=run_id,
        crash_after_tools=2
    )
except SimulatedCrash as error:
    print("Crash simulated:", error)

print("\n========== RESUMING FROM CHECKPOINT ==========")

result = resume_agent(run_id)

print("Status:", result["status"])
print("Final answer:", result["final_answer"])
print("LLM calls:", result["llm_calls"])
print("Tokens used:", result["tokens_used"])

print("\nTools executed in completed run:")
for step in result["steps"]:
    print("-", step["tool"])

print("\nCheckpoint file:")
print(ROOT / "state" / f"{run_id}.json")