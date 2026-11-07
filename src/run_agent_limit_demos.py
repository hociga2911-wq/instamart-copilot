
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent import run_agent

SCENARIOS_FILE = ROOT / "data" / "raw" / "agent_scenarios.csv"

with SCENARIOS_FILE.open(
    newline="", encoding="utf-8"
) as file:
    scenarios = list(csv.DictReader(file))

s1 = next(
    scenario for scenario in scenarios
    if scenario["scenario_id"] == "S1"
)

print("========== TOKEN LIMIT DEMO ==========")

token_result = run_agent(
    user_message=s1["message"],
    scenario_id="S1_TOKEN_LIMIT_DEMO",
    run_id="token_limit_demo_200",
    token_limit=200
)

print("Status:", token_result["status"])
print("LLM calls:", token_result["llm_calls"])
print("Tokens used:", token_result["tokens_used"])
print("Tools executed:", [
    step["tool"] for step in token_result["steps"]
])
print("Final answer:", token_result["final_answer"])

print("\n========== TIMEOUT DEMO ==========")

timeout_result = run_agent(
    user_message=s1["message"],
    scenario_id="S1_TIMEOUT_DEMO",
    run_id="timeout_demo_zero",
    time_limit_seconds=0
)

print("Status:", timeout_result["status"])
print("LLM calls:", timeout_result["llm_calls"])
print("Tokens used:", timeout_result["tokens_used"])
print("Tools executed:", [
    step["tool"] for step in timeout_result["steps"]
])
print("Final answer:", timeout_result["final_answer"])
