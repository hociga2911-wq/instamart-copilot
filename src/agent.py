

"""Part D: ReAct customer support agent with guardrails and checkpoints."""

from pathlib import Path
from datetime import datetime, timezone
import json
import time
import uuid
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import mock_llm
from agent_tools import TOOLS_SPEC, execute_tool

STATE_DIR = ROOT / "state"
OUTPUT_DIR = ROOT / "outputs"
RUNS_FILE = OUTPUT_DIR / "agent_runs.jsonl"


SYSTEM_PROMPT = """You are an AGENT for Instamart customer support.

Use the available tools to investigate order refund requests.
Always look up the order before deciding refund eligibility.
Only completed orders can receive refunds.
Orders delivered in more than 45 minutes qualify for a full refund.
Refunds above INR 1000 must be escalated to a human support lead.
Refunds of INR 1000 or less may be issued automatically.
Cancelled orders must never receive a refund.

Use tools when needed. Do not invent order information.
Give a concise final response with an appropriate status prefix:
REFUND, ESCALATE, DENIED, or NOT_FOUND.
"""


class SimulatedCrash(Exception):
    """Used only for the checkpoint recovery demonstration."""


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_path(run_id):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{run_id}.json"


def _save_checkpoint(run_id, state):
    """Save the complete agent state atomically."""
    path = _checkpoint_path(run_id)
    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )

    temporary.replace(path)


def _load_checkpoint(run_id):
    path = _checkpoint_path(run_id)

    if not path.exists():
        raise FileNotFoundError(
            f"No checkpoint exists for run {run_id}"
        )

    return json.loads(path.read_text(encoding="utf-8"))


def _append_run_log(record):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with RUNS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def _status_from_answer(answer):
    """Derive a stable status from the final response prefix."""
    prefixes = (
        "FALLBACK_TIMEOUT",
        "FALLBACK_TOKEN_LIMIT",
        "FALLBACK_MAX_ITERATIONS",
        "NOT_FOUND",
        "ESCALATE",
        "REFUND",
        "DENIED",
        "NEEDS_INFO"
    )

    for prefix in prefixes:
        if answer.startswith(prefix):
            return prefix

    if answer.startswith("FALLBACK"):
        return "FALLBACK"

    return "COMPLETED"


def _new_state(user_message, scenario_id):
    return {
        "run_id": str(uuid.uuid4()),
        "scenario_id": str(scenario_id),
        "user_message": user_message,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "tokens_used": 0,
        "llm_calls": 0,
        "step_number": 0,
        "tools_executed": [],
        "steps": [],
        "status": "RUNNING",
        "final_answer": None,
        "created_at": _utc_now()
    }


def _finish(state, answer):
    state["final_answer"] = answer
    state["status"] = _status_from_answer(answer)
    state["completed_at"] = _utc_now()

    record = {
        "scenario_id": state["scenario_id"],
        "status": state["status"],
        "final_answer": answer,
        "llm_calls": state["llm_calls"],
        "tokens_used": state["tokens_used"],
        "steps": state["steps"]
    }

    _append_run_log(record)
    _save_checkpoint(state["run_id"], state)

    return record


def run_agent(
    user_message,
    scenario_id,
    max_iterations=6,
    token_limit=6000,
    time_limit_seconds=10,
    run_id=None,
    resume=False,
    crash_after_tools=None
):
    """Run or resume a tool-using ReAct agent.

    Optional recovery/demo arguments:
        run_id: Existing checkpoint identifier.
        resume: Load an existing checkpoint.
        crash_after_tools: Simulate a crash after this many
                           tool executions in the current run.
    """

    if resume:
        if not run_id:
            raise ValueError("run_id is required when resume=True")

        state = _load_checkpoint(run_id)

        if state["status"] != "RUNNING":
            return {
                "scenario_id": state["scenario_id"],
                "status": state["status"],
                "final_answer": state["final_answer"],
                "llm_calls": state["llm_calls"],
                "tokens_used": state["tokens_used"],
                "steps": state["steps"]
            }

    else:
        state = _new_state(user_message, scenario_id)

        if run_id:
            state["run_id"] = run_id

        _save_checkpoint(state["run_id"], state)

    started = time.monotonic()
    tools_this_call = 0

    for iteration in range(max_iterations):

        # Check the time limit before every model call.
        if time.monotonic() - started >= time_limit_seconds:
            return _finish(
                state,
                "FALLBACK_TIMEOUT: Time limit reached. "
                "Please hand this case to a human support agent."
            )

        response = mock_llm.chat(
            state["messages"],
            tools=TOOLS_SPEC
        )

        state["llm_calls"] += 1

        usage = getattr(response, "usage", None)
        call_tokens = getattr(usage, "total_tokens", 0)
        state["tokens_used"] += call_tokens

        message = response.choices[0].message

        # Check token budget immediately after the model call.
        # Do not execute a tool if the budget has been exceeded.
        if state["tokens_used"] > token_limit:
            return _finish(
                state,
                "FALLBACK_TOKEN_LIMIT: Token budget exceeded. "
                "Please hand this case to a human support agent."
            )

        tool_calls = getattr(message, "tool_calls", None) or []

        if not tool_calls:
            final_answer = message.content or (
                "DENIED: No final response was provided."
            )

            return _finish(state, final_answer)

        # Record the assistant's tool requests in message history.
        state["messages"].append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "name": call.name,
                    "arguments": call.arguments
                }
                for call in tool_calls
            ]
        })

        for call in tool_calls:
            tool_name = call.name
            arguments = call.arguments

            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            if not isinstance(arguments, dict):
                arguments = {}

            observation = execute_tool(
                tool_name,
                arguments
            )

            state["step_number"] += 1
            tools_this_call += 1
            state["tools_executed"].append(tool_name)

            state["steps"].append({
                "step": state["step_number"],
                "tool": tool_name,
                "arguments": arguments,
                "observation": observation
            })

            state["messages"].append({
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(observation)
            })

            # Save a checkpoint after every tool observation.
            _save_checkpoint(state["run_id"], state)

            # Simulate a crash for the recovery demonstration.
            if (
                crash_after_tools is not None
                and tools_this_call == crash_after_tools
            ):
                raise SimulatedCrash(
                    f"Simulated crash after tool {tool_name}. "
                    f"Resume using run_id={state['run_id']}"
                )

    return _finish(
        state,
        "FALLBACK_MAX_ITERATIONS: Maximum agent iterations reached. "
        "Please hand this case to a human support agent."
    )

def resume_agent(run_id):
    """Resume an interrupted agent run from its latest checkpoint."""
    state = _load_checkpoint(run_id)

    if state["status"] != "RUNNING":
        return {
            "scenario_id": state["scenario_id"],
            "status": state["status"],
            "final_answer": state["final_answer"],
            "llm_calls": state["llm_calls"],
            "tokens_used": state["tokens_used"],
            "steps": state["steps"]
        }

    return run_agent(
        user_message=state["user_message"],
        scenario_id=state["scenario_id"],
        run_id=run_id,
        resume=True
    )

if __name__ == "__main__":
    print("ReAct agent module loaded.")
    print("Checkpoint directory:", STATE_DIR)
    print("Run log:", RUNS_FILE)
    print("No refund or escalation is executed by this smoke test.")
