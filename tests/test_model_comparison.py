"""
Model Comparison Test Harness

Replays real conversations from the past N days against all supported models.
All (model × test-case) tasks run concurrently under a semaphore cap (default 20).

READ tools  → executed against real Firestore (read-only, no side effects)
WRITE tools → mocked with plausible success responses (no Firestore writes)

Scoring:
  Score = % of test cases where tool selection exactly matches the reference model.
  Reference model (claude-sonnet-4-6) always scores 100.

Grades:  A=90-100  B=80-89  C=70-79  D=55-69  F=0-54

Usage:
    python tests/test_model_comparison.py
    python tests/test_model_comparison.py --days 14
    python tests/test_model_comparison.py --output results.csv --concurrency 10
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import functools
import json
import sys
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from backend.model_client import UnifiedModelClient, SUPPORTED_MODELS
from backend.firebase_client import FirebaseClient
from backend.system_prompts import get_expense_parsing_system_prompt
from backend.mcp.expense_server import (
    handle_list_tools,
    _get_budget_status,
    _get_categories,
    _get_recent_expenses,
    _search_expenses,
    _query_expenses,
    _get_spending_by_category,
    _get_spending_summary,
    _get_budget_remaining,
    _compare_periods,
    _get_largest_expenses,
    _list_recurring_expenses,
)

# ── constants ─────────────────────────────────────────────────────────────────

REFERENCE_MODEL = "claude-sonnet-4-6"
CONCURRENCY_LIMIT = 20


def _bypass_auth(token, *args, **kwargs) -> str:
    """
    Single top-level auth bypass used for the entire test run.
    Each task encodes its user_id as "test_harness::<uid>" so concurrent
    tasks with different users resolve correctly without per-coroutine patching.
    """
    if isinstance(token, str) and token.startswith("test_harness::"):
        return token.split("::", 1)[1]
    raise RuntimeError(f"Test harness: unexpected auth token: {token!r}")

WRITE_TOOLS: set[str] = {
    "save_expense",
    "update_expense",
    "delete_expense",
    "create_recurring_expense",
    "delete_recurring_expense",
}

READ_TOOL_HANDLERS: dict[str, object] = {
    "get_budget_status": _get_budget_status,
    "get_categories": _get_categories,
    "get_recent_expenses": _get_recent_expenses,
    "search_expenses": _search_expenses,
    "query_expenses": _query_expenses,
    "get_spending_by_category": _get_spending_by_category,
    "get_spending_summary": _get_spending_summary,
    "get_budget_remaining": _get_budget_remaining,
    "compare_periods": _compare_periods,
    "get_largest_expenses": _get_largest_expenses,
    "list_recurring_expenses": _list_recurring_expenses,
}


# ── write mocks ───────────────────────────────────────────────────────────────

def get_mock_write_result(tool_name: str, args: dict) -> str:
    """Return a plausible JSON success payload for write tools (no actual Firestore write)."""
    if tool_name == "save_expense":
        return json.dumps({
            "success": True,
            "expense_id": "mock_expense_id_dryrun",
            "expense_name": args.get("name", "Unknown"),
            "amount": args.get("amount", 0),
            "category": args.get("category", "OTHER"),
        })
    if tool_name == "update_expense":
        return json.dumps({
            "success": True,
            "expense_id": args.get("expense_id", "mock_id"),
            "expense_name": args.get("name"),
            "amount": args.get("amount"),
            "category": args.get("category"),
        })
    if tool_name == "delete_expense":
        return json.dumps({
            "success": True,
            "expense_id": args.get("expense_id", "mock_id"),
            "deleted_expense": {"name": "Mock expense", "amount": 0, "category": "OTHER"},
        })
    if tool_name == "create_recurring_expense":
        name = args.get("name", "Unknown")
        amount = args.get("amount", 0)
        frequency = args.get("frequency", "monthly")
        return json.dumps({
            "success": True,
            "template_id": "mock_template_id_dryrun",
            "expense_name": name,
            "amount": amount,
            "category": args.get("category", "OTHER"),
            "frequency": frequency,
            "message": f"Created recurring expense: {name} (${amount:.2f} {frequency})",
        })
    if tool_name == "delete_recurring_expense":
        return json.dumps({
            "success": True,
            "template_id": args.get("template_id", "mock_id"),
            "message": "Deleted recurring expense (dry-run)",
        })
    return json.dumps({"success": True})


# ── core runner ───────────────────────────────────────────────────────────────

async def run_model_on_case(
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools_anthro: list[dict],
    user_id: str,
) -> dict:
    """
    Run a single model against one conversation turn.

    * READ tools  → dispatched to the real async handler (real Firestore reads)
    * WRITE tools → short-circuited to get_mock_write_result (no writes)
    * verify_token_and_get_uid is patched to return user_id directly

    Returns a result dict with model, tools_called, final_response, token counts,
    elapsed_s, and an error field (None if successful).
    """
    loop = asyncio.get_running_loop()

    run_messages: list[dict] = list(messages)
    tools_called: list[str] = []
    total_input = 0
    total_output = 0
    final_response: str = ""
    error: str | None = None

    t0 = time.monotonic()

    try:
        client = UnifiedModelClient(model)

        for _turn in range(10):  # cap tool-call rounds at 10
            msgs_snapshot = list(run_messages)

            response = await loop.run_in_executor(
                None,
                functools.partial(
                    client.create,
                    system_prompt,
                    msgs_snapshot,
                    tools_anthro,
                ),
            )

            total_input += response.input_tokens
            total_output += response.output_tokens

            if response.stop_reason == "end_turn" or not response.tool_calls:
                final_response = response.content or ""
                break

            asst_content: list[dict] = []
            if response.content:
                asst_content.append({"type": "text", "text": response.content})
            for tc in response.tool_calls:
                asst_content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            run_messages.append({"role": "assistant", "content": asst_content})

            tool_result_blocks: list[dict] = []
            for tc in response.tool_calls:
                tools_called.append(tc.name)

                # Encode user_id in the token so the top-level bypass can extract it
                args = dict(tc.arguments)
                args["auth_token"] = f"test_harness::{user_id}"

                if tc.name in WRITE_TOOLS:
                    result_text = get_mock_write_result(tc.name, args)
                elif tc.name in READ_TOOL_HANDLERS:
                    try:
                        result_list = await READ_TOOL_HANDLERS[tc.name](args)
                        result_text = result_list[0].text if result_list else "{}"
                    except Exception as handler_err:
                        result_text = json.dumps({"error": str(handler_err)})
                else:
                    result_text = json.dumps({"error": f"Unknown tool: {tc.name}"})

                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_text,
                })

            run_messages.append({"role": "user", "content": tool_result_blocks})

        else:
            final_response = final_response or "[max turns reached]"

    except Exception as exc:
        error = str(exc)
        final_response = f"[ERROR: {exc}]"

    elapsed = time.monotonic() - t0

    return {
        "model": model,
        "tools_called": tools_called,
        "final_response": final_response,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "elapsed_s": elapsed,
        "error": error,
    }


async def run_with_sem(
    sem: asyncio.Semaphore,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools_anthro: list[dict],
    user_id: str,
    case_idx: int,
    conv_id: str,
    user_message: str,
    expected_tools: list[str],
) -> dict:
    """Acquire the semaphore, run the model, attach metadata."""
    async with sem:
        result = await run_model_on_case(model, system_prompt, messages, tools_anthro, user_id)
    result["case_idx"] = case_idx
    result["conv_id"] = conv_id
    result["user_message"] = user_message
    result["expected_tools"] = expected_tools
    return result


# ── conversation fetching ─────────────────────────────────────────────────────

def fetch_recent_conversations(days: int = 7) -> list[dict]:
    """
    Fetch conversations active within the past `days` days, for all users.
    Returns a list of conversation dicts, each augmented with a 'user_id' key.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    global_client = FirebaseClient()
    user_docs = list(global_client.db.collection("users").stream())
    print(f"Found {len(user_docs)} user(s) in Firestore")

    all_conversations: list[dict] = []
    for user_doc in user_docs:
        user_id = user_doc.id
        user_client = FirebaseClient.for_user(user_id)

        try:
            conversations = user_client.list_conversations(limit=100)
        except Exception as exc:
            print(f"  [warn] Could not list conversations for {user_id}: {exc}")
            continue

        for conv in conversations:
            last_activity = conv.get("last_activity")
            if last_activity is None:
                continue

            la_dt = last_activity
            if hasattr(la_dt, "tzinfo") and la_dt.tzinfo is None:
                la_dt = la_dt.replace(tzinfo=timezone.utc)

            if la_dt >= cutoff:
                conv["user_id"] = user_id
                all_conversations.append(conv)

    return all_conversations


def extract_test_cases(conversation: dict) -> list[dict]:
    """
    Extract individual user turns from a conversation as test cases.

    Each returned dict contains:
      - user_message:     the user's text for this turn
      - prior_messages:   preceding conversation context (role/content pairs)
      - expected_tools:   tools recorded in the following assistant message
      - expected_response: the following assistant message content
    """
    messages: list[dict] = conversation.get("messages", [])
    test_cases: list[dict] = []

    for i, msg in enumerate(messages):
        if msg.get("role") != "user":
            continue

        content = msg.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        expected_tools: list[str] = []
        expected_response = ""
        for j in range(i + 1, len(messages)):
            nxt = messages[j]
            if nxt.get("role") == "assistant":
                raw_calls = nxt.get("tool_calls", [])
                expected_tools = [
                    tc.get("name", "") for tc in raw_calls if isinstance(tc, dict)
                ]
                expected_response = nxt.get("content", "")
                break

        prior_messages: list[dict] = []
        for m in messages[:i]:
            role = m.get("role")
            body = m.get("content", "")
            if role in ("user", "assistant") and isinstance(body, str) and body.strip():
                prior_messages.append({"role": role, "content": body})

        test_cases.append({
            "user_message": content.strip(),
            "prior_messages": prior_messages,
            "expected_tools": expected_tools,
            "expected_response": expected_response,
        })

    return test_cases


# ── output formatting ─────────────────────────────────────────────────────────

def _ref_tools_from_group(case_results: list[dict]) -> set[str]:
    for r in case_results:
        if r["model"] == REFERENCE_MODEL:
            return set(r["tools_called"])
    return set()


def print_comparison(case_idx: int, user_message: str, expected_tools: list[str], results: list[dict]) -> None:
    ref_set = _ref_tools_from_group(results)

    print(f"\n{'='*100}")
    msg_preview = user_message[:90].replace("\n", " ")
    print(f"Case #{case_idx}:  \"{msg_preview}\"")
    if expected_tools:
        print(f"  Original tools (from Firestore log): {expected_tools}")
    print(f"{'='*100}")

    col_model = 26
    col_tools = 35
    print(
        f"{'Model':<{col_model}} {'Tools Called':<{col_tools}} {'Match':>5}"
        f" {'In+Out':>10} {'Sec':>6}  Response Preview"
    )
    print("-" * 100)

    model_order = list(SUPPORTED_MODELS.keys())
    for r in sorted(results, key=lambda r: model_order.index(r["model"]) if r["model"] in model_order else 99):
        model_name = r["model"]
        tools = r["tools_called"]
        tools_str = ", ".join(tools) if tools else "(none)"
        if len(tools_str) > col_tools - 2:
            tools_str = tools_str[: col_tools - 5] + "..."

        if model_name == REFERENCE_MODEL:
            match_str = " REF"
        elif set(tools) == ref_set:
            match_str = "  OK"
        else:
            match_str = "DIFF"

        tok = f"{r['input_tokens']}+{r['output_tokens']}"
        sec = f"{r['elapsed_s']:.1f}s"

        resp = (r["final_response"] or "").replace("\n", " ")[:65]
        if r.get("error"):
            resp = f"[ERROR] {r['error'][:60]}"

        print(
            f"{model_name:<{col_model}} {tools_str:<{col_tools}} {match_str:>5}"
            f" {tok:>10} {sec:>6}  {resp}"
        )

    print()


# ── scoring + CSV ─────────────────────────────────────────────────────────────

def letter_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"


def build_aggregate(all_results: list[dict]) -> dict[str, dict]:
    """
    Compute per-model aggregate stats.
    Score = % of cases where tool set exactly matches the reference model.
    """
    ref_by_case: dict[int, set[str]] = {}
    for r in all_results:
        if r["model"] == REFERENCE_MODEL:
            ref_by_case[r["case_idx"]] = set(r["tools_called"])

    stats: dict[str, dict] = {
        m: {"total": 0, "matched": 0, "input": 0, "output": 0, "elapsed": 0.0, "errors": 0}
        for m in SUPPORTED_MODELS
    }

    for r in all_results:
        m = r["model"]
        s = stats[m]
        s["total"] += 1
        s["input"] += r["input_tokens"]
        s["output"] += r["output_tokens"]
        s["elapsed"] += r["elapsed_s"]
        if r.get("error"):
            s["errors"] += 1
        ref_set = ref_by_case.get(r["case_idx"], set())
        if set(r["tools_called"]) == ref_set:
            s["matched"] += 1

    total_cases = len(ref_by_case)

    agg: dict[str, dict] = {}
    for model, s in stats.items():
        n = s["total"] or 1
        score = (s["matched"] / n * 100) if n else 0.0
        agg[model] = {
            "model": model,
            "provider": SUPPORTED_MODELS[model]["provider"],
            "total_cases": total_cases,
            "matched": s["matched"],
            "pass_rate": f"{s['matched']}/{n}",
            "score": round(score, 1),
            "grade": letter_grade(score),
            "avg_elapsed": round(s["elapsed"] / n, 2),
            "total_input": s["input"],
            "total_output": s["output"],
            "total_tokens": s["input"] + s["output"],
            "avg_input": round(s["input"] / n),
            "avg_output": round(s["output"] / n),
            "errors": s["errors"],
        }

    return agg


def print_aggregate_summary(agg: dict[str, dict], total_cases: int) -> None:
    print(f"\n{'='*100}")
    print(f"Aggregate Summary  ({total_cases} test case(s), {len(SUPPORTED_MODELS)} model(s))")
    print(f"{'='*100}")
    print(
        f"{'Model':<26} {'Score':>7} {'Grade':>6} {'Pass Rate':>10}"
        f" {'Tot Tokens':>11} {'Avg In':>8} {'Avg Out':>8} {'Avg Sec':>8}  {'Errors':>6}"
    )
    print("-" * 102)

    for model in SUPPORTED_MODELS:
        s = agg[model]
        note = " (ref)" if model == REFERENCE_MODEL else ""
        print(
            f"{model:<26} {s['score']:>6.1f}%{note:<1} {s['grade']:>6} {s['pass_rate']:>10}"
            f" {s['total_tokens']:>11,} {s['avg_input']:>8.0f} {s['avg_output']:>8.0f}"
            f" {s['avg_elapsed']:>7.1f}s  {s['errors']:>6}"
        )

    print(f"\nTotal test cases : {total_cases}")
    print(f"Models tested    : {len(SUPPORTED_MODELS)}")


DETAIL_FIELDS = [
    "case_idx", "conv_id", "user_message", "model", "provider",
    "tool_match", "tools_called", "ref_tools", "expected_tools",
    "input_tokens", "output_tokens", "total_tokens", "elapsed_s", "response_preview", "error",
]

SUMMARY_FIELDS = [
    "model", "provider", "pass_rate", "score", "grade",
    "avg_elapsed_s", "total_tokens", "total_input_tokens", "total_output_tokens",
    "avg_input_tokens", "avg_output_tokens", "errors",
]


def write_csv(all_results: list[dict], agg: dict[str, dict], output_path: str) -> None:
    # Build ref_tools lookup
    ref_by_case: dict[int, set[str]] = {}
    for r in all_results:
        if r["model"] == REFERENCE_MODEL:
            ref_by_case[r["case_idx"]] = set(r["tools_called"])

    model_order = list(SUPPORTED_MODELS.keys())
    sorted_results = sorted(
        all_results,
        key=lambda r: (r["case_idx"], model_order.index(r["model"]) if r["model"] in model_order else 99),
    )

    with open(output_path, "w", newline="") as f:
        # ── per-case detail rows ──
        writer = csv.DictWriter(f, fieldnames=DETAIL_FIELDS)
        writer.writeheader()

        for r in sorted_results:
            ref_set = ref_by_case.get(r["case_idx"], set())
            tool_match = "REF" if r["model"] == REFERENCE_MODEL else ("OK" if set(r["tools_called"]) == ref_set else "DIFF")
            writer.writerow({
                "case_idx": r["case_idx"],
                "conv_id": r["conv_id"],
                "user_message": r["user_message"][:120].replace("\n", " "),
                "model": r["model"],
                "provider": SUPPORTED_MODELS[r["model"]]["provider"],
                "tool_match": tool_match,
                "tools_called": ", ".join(r["tools_called"]) or "(none)",
                "ref_tools": ", ".join(sorted(ref_set)) or "(none)",
                "expected_tools": ", ".join(r["expected_tools"]) or "(none)",
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "total_tokens": r["input_tokens"] + r["output_tokens"],
                "elapsed_s": round(r["elapsed_s"], 2),
                "response_preview": (r["final_response"] or "").replace("\n", " ")[:100],
                "error": r["error"] or "",
            })

        f.write("\n")

        # ── model summary ──
        f.write("=== MODEL SUMMARY ===\n")
        summary_writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        summary_writer.writeheader()

        for model in SUPPORTED_MODELS:
            s = agg[model]
            summary_writer.writerow({
                "model": model,
                "provider": s["provider"],
                "pass_rate": s["pass_rate"],
                "score": s["score"],
                "grade": s["grade"],
                "avg_elapsed_s": s["avg_elapsed"],
                "total_tokens": s["total_tokens"],
                "total_input_tokens": s["total_input"],
                "total_output_tokens": s["total_output"],
                "avg_input_tokens": s["avg_input"],
                "avg_output_tokens": s["avg_output"],
                "errors": s["errors"],
            })

        f.write("\n")
        f.write("=== SCORING KEY ===\n")
        f.write("Score = % of test cases where tool selection exactly matches the reference model (claude-sonnet-4-6)\n")
        f.write("Grades: A=90-100  B=80-89  C=70-79  D=55-69  F=0-54\n")
        f.write(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# ── main ──────────────────────────────────────────────────────────────────────

async def main(days: int, concurrency: int, output: str) -> None:
    print("=" * 100)
    print(f"Model Comparison Test Harness  —  replaying past {days} day(s) of conversations")
    print("=" * 100)
    print(f"Models      : {list(SUPPORTED_MODELS.keys())}")
    print(f"Reference   : {REFERENCE_MODEL}")
    print(f"Concurrency : {concurrency} simultaneous tasks")
    print()

    # Build tools list once
    tools_mcp = await handle_list_tools()
    tools_anthro: list[dict] = []
    for t in tools_mcp:
        schema = t.inputSchema
        if not isinstance(schema, dict):
            try:
                schema = dict(schema)
            except Exception:
                schema = {}
        tools_anthro.append({
            "name": t.name,
            "description": t.description or "",
            "input_schema": schema,
        })
    print(f"Loaded {len(tools_anthro)} MCP tool(s)")

    system_prompt = get_expense_parsing_system_prompt()

    print(f"\nFetching conversations active in the past {days} day(s)...")
    conversations = fetch_recent_conversations(days=days)
    print(f"Found {len(conversations)} qualifying conversation(s)\n")

    if not conversations:
        print("No recent conversations found. Exiting.")
        print("Tip: try --days 30 to extend the look-back window.")
        return

    # ── collect all test cases upfront ────────────────────────────────────────
    all_cases: list[dict] = []
    case_idx = 0

    for conv in conversations:
        user_id = conv["user_id"]
        conv_id = conv.get("conversation_id", "unknown")
        test_cases = extract_test_cases(conv)

        for tc in test_cases:
            case_idx += 1
            all_cases.append({
                "case_idx": case_idx,
                "conv_id": conv_id,
                "user_id": user_id,
                "user_message": tc["user_message"],
                "messages": tc["prior_messages"] + [{"role": "user", "content": tc["user_message"]}],
                "expected_tools": tc["expected_tools"],
            })

    if not all_cases:
        print("No extractable test cases found in the fetched conversations.")
        return

    total_tasks = len(all_cases) * len(SUPPORTED_MODELS)
    print(f"Test cases  : {len(all_cases)}")
    print(f"Total tasks : {total_tasks}  ({len(all_cases)} cases × {len(SUPPORTED_MODELS)} models)")
    print(f"Dispatching all tasks now (semaphore={concurrency})...\n")

    # ── dispatch all tasks concurrently under semaphore ───────────────────────
    sem = asyncio.Semaphore(concurrency)
    completed = 0

    # Patch once at the top level so concurrent coroutines don't trample each other.
    # Per-coroutine patching caused a race: one coroutine's context exit would
    # restore the real function while another coroutine was still mid-flight.
    tasks = [
        run_with_sem(
            sem,
            model,
            system_prompt,
            case["messages"],
            tools_anthro,
            case["user_id"],
            case["case_idx"],
            case["conv_id"],
            case["user_message"],
            case["expected_tools"],
        )
        for case in all_cases
        for model in SUPPORTED_MODELS
    ]

    all_results: list[dict] = []
    with patch(
        "backend.mcp.expense_server.verify_token_and_get_uid",
        side_effect=_bypass_auth,
    ):
        for coro in asyncio.as_completed(tasks):
            r = await coro
            completed += 1
            tools_str = ", ".join(r["tools_called"]) or "(none)"
            tag = "[ERR]" if r.get("error") else "[ ok]"
            print(
                f"  {tag}  [{completed:>3}/{total_tasks}]  "
                f"{r['model']:<26}  case #{r['case_idx']}  "
                f"{r['elapsed_s']:.1f}s  tools: {tools_str[:40]}"
            )
            all_results.append(r)

    # ── print per-case comparison tables ──────────────────────────────────────
    by_case: dict[int, list[dict]] = defaultdict(list)
    for r in all_results:
        by_case[r["case_idx"]].append(r)

    for idx in sorted(by_case.keys()):
        case_results = by_case[idx]
        sample = case_results[0]
        print_comparison(idx, sample["user_message"], sample["expected_tools"], case_results)

    # ── aggregate + output ────────────────────────────────────────────────────
    agg = build_aggregate(all_results)
    total_cases = len(by_case)

    print_aggregate_summary(agg, total_cases)

    write_csv(all_results, agg, output)
    print(f"\nCSV written → {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replay real conversations against all models concurrently and compare tool decisions."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of conversation history to replay (default: 7)",
    )
    parser.add_argument(
        "--output",
        default="model_comparison.csv",
        help="CSV output file path (default: model_comparison.csv)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=CONCURRENCY_LIMIT,
        help=f"Max simultaneous (model, case) tasks (default: {CONCURRENCY_LIMIT})",
    )
    args = parser.parse_args()

    asyncio.run(main(days=args.days, concurrency=args.concurrency, output=args.output))
