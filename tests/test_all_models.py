"""
Smoke test for all models in UnifiedModelClient.

Calls each model concurrently (async) with a set of simple prompts.
Runs at most 20 API calls at a time via an asyncio semaphore.
Writes results to a CSV with per-model scores and letter grades.

Scoring per test case (0-100):
  40 pts  connected and returned a non-empty response
  30 pts  response contains the expected text
  20 pts  response exactly matches the expected text (precise)
  10 pts  speed rank among passing models (1st = 10 pts, last ≈ 0 pts)

Per-model aggregate score = average across all test cases.

Grades:
  A  90-100    B  80-89    C  70-79    D  55-69    F  0-54

Usage:
    python tests/test_all_models.py
    python tests/test_all_models.py --output results.csv
    python tests/test_all_models.py --concurrency 10
"""

from __future__ import annotations

import sys
import os
import csv
import asyncio
import functools
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from backend.model_client import UnifiedModelClient, SUPPORTED_MODELS

SYSTEM = "You are a helpful assistant."

# Each entry: (user_message, expected_text)
TEST_CASES: list[tuple[str, str]] = [
    ("Reply with exactly: OK", "OK"),
    ("What is 2 + 2? Reply with just the number.", "4"),
    ("Is Python a programming language? Reply with just Yes or No.", "Yes"),
    ("What is the capital of France? Reply with just the city name.", "Paris"),
    ("Translate 'hello' to Spanish. Reply with just the word.", "hola"),
]

FIELDNAMES = [
    "model", "provider", "case_idx", "prompt", "expected",
    "status", "score", "grade", "response", "elapsed_s",
    "input_tokens", "output_tokens", "error",
]

CONCURRENCY_LIMIT = 20  # max simultaneous API calls


# ── scoring ───────────────────────────────────────────────────────────────────

def compute_case_score(passed: bool, response: str, expected: str, speed_rank: int, total_passing: int) -> int:
    if not passed:
        return 0

    score = 40  # connected and returned non-empty response

    resp = response.strip().lower()
    exp = expected.strip().lower()

    if exp in resp:
        score += 30       # contains expected text
    if resp == exp:
        score += 20       # exactly the expected text

    # Speed: linearly distribute 0-10 pts across rank positions
    if total_passing > 1:
        speed_pts = round(10 * (total_passing - speed_rank) / (total_passing - 1))
    else:
        speed_pts = 10
    score += speed_pts

    return score


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


# ── async runner ──────────────────────────────────────────────────────────────

async def run_one(
    sem: asyncio.Semaphore,
    loop: asyncio.AbstractEventLoop,
    model: str,
    case_idx: int,
    prompt: str,
    expected: str,
) -> dict:
    """Run one (model, prompt) pair under the semaphore; return a raw result dict."""
    async with sem:
        t0 = time.monotonic()
        try:
            client = UnifiedModelClient(model)
            messages = [{"role": "user", "content": prompt}]

            response = await loop.run_in_executor(
                None,
                functools.partial(
                    client.create,
                    SYSTEM,
                    messages,
                    [],          # no tools
                    500,         # max_tokens
                ),
            )

            elapsed = time.monotonic() - t0

            if response.content and response.content.strip():
                return {
                    "model": model,
                    "provider": SUPPORTED_MODELS[model]["provider"],
                    "case_idx": case_idx,
                    "prompt": prompt,
                    "expected": expected,
                    "status": "PASS",
                    "response": response.content.strip(),
                    "elapsed_s": round(elapsed, 2),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "error": "",
                }
            else:
                return {
                    "model": model,
                    "provider": SUPPORTED_MODELS[model]["provider"],
                    "case_idx": case_idx,
                    "prompt": prompt,
                    "expected": expected,
                    "status": "FAIL",
                    "response": "",
                    "elapsed_s": round(elapsed, 2),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "error": "Empty response",
                }

        except Exception as exc:
            elapsed = time.monotonic() - t0
            return {
                "model": model,
                "provider": SUPPORTED_MODELS[model]["provider"],
                "case_idx": case_idx,
                "prompt": prompt,
                "expected": expected,
                "status": "FAIL",
                "response": "",
                "elapsed_s": round(elapsed, 2),
                "input_tokens": 0,
                "output_tokens": 0,
                "error": str(exc),
            }


async def run_all(concurrency: int = CONCURRENCY_LIMIT) -> list[dict]:
    """
    Build one task per (model, test_case) pair.
    Run all tasks with at most `concurrency` active at once.
    Return results sorted by (case_idx, model).
    """
    models = list(SUPPORTED_MODELS.keys())
    total_calls = len(models) * len(TEST_CASES)
    print(f"Total API calls: {total_calls}  ({len(models)} models × {len(TEST_CASES)} prompts)")
    print(f"Concurrency cap: {concurrency}\n")

    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()
    completed = 0

    tasks = [
        run_one(sem, loop, model, case_idx + 1, prompt, expected)
        for case_idx, (prompt, expected) in enumerate(TEST_CASES)
        for model in models
    ]

    results: list[dict] = []
    for coro in asyncio.as_completed(tasks):
        r = await coro
        completed += 1
        tag = "[PASS]" if r["status"] == "PASS" else "[FAIL]"
        print(
            f"  {tag}  [{completed:>2}/{total_calls}]  "
            f"{r['model']:<26}  case #{r['case_idx']}  "
            f"{r['elapsed_s']:.2f}s  →  {r['response'] or r['error']}"
        )
        results.append(r)

    # Sort: case first, then model in canonical order
    model_order = {m: i for i, m in enumerate(models)}
    results.sort(key=lambda r: (r["case_idx"], model_order.get(r["model"], 999)))
    return results


# ── scoring pass ──────────────────────────────────────────────────────────────

def assign_scores(results: list[dict]) -> list[dict]:
    """
    Compute case-level scores with speed ranked within each (case, passing-models) group.
    Adds 'score' and 'grade' to every row in-place.
    """
    # Group by case_idx
    from collections import defaultdict
    by_case: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for i, r in enumerate(results):
        by_case[r["case_idx"]].append((i, r))

    for case_rows in by_case.values():
        passing = sorted(
            [(i, r) for i, r in case_rows if r["status"] == "PASS"],
            key=lambda x: x[1]["elapsed_s"],
        )
        speed_rank_by_idx = {idx: rank for rank, (idx, _) in enumerate(passing, start=1)}
        total_passing = len(passing)

        for i, r in case_rows:
            if r["status"] == "PASS":
                rank = speed_rank_by_idx.get(i, total_passing)
                sc = compute_case_score(True, r["response"], r["expected"], rank, total_passing)
            else:
                sc = 0
            r["score"] = sc
            r["grade"] = letter_grade(sc)

    return results


def aggregate_by_model(results: list[dict]) -> dict[str, dict]:
    """
    Average scores across test cases per model and compute an overall grade.
    Returns {model: {avg_score, grade, passed, total, avg_elapsed, ...}}.
    """
    models = list(SUPPORTED_MODELS.keys())
    agg: dict[str, dict] = {
        m: {
            "model": m,
            "provider": SUPPORTED_MODELS[m]["provider"],
            "passed": 0,
            "total": 0,
            "total_score": 0,
            "total_elapsed": 0.0,
            "total_input": 0,
            "total_output": 0,
            "errors": 0,
        }
        for m in models
    }

    for r in results:
        m = r["model"]
        s = agg[m]
        s["total"] += 1
        s["total_score"] += r["score"]
        s["total_elapsed"] += r["elapsed_s"]
        s["total_input"] += r["input_tokens"]
        s["total_output"] += r["output_tokens"]
        if r["status"] == "PASS":
            s["passed"] += 1
        if r["error"]:
            s["errors"] += 1

    for s in agg.values():
        n = s["total"] or 1
        s["avg_score"] = round(s["total_score"] / n, 1)
        s["grade"] = letter_grade(s["avg_score"])
        s["avg_elapsed"] = round(s["total_elapsed"] / n, 2)
        s["avg_input"] = round(s["total_input"] / n)
        s["avg_output"] = round(s["total_output"] / n)
        s["pass_rate"] = f"{s['passed']}/{s['total']}"

    return agg


# ── CSV writer ────────────────────────────────────────────────────────────────

def _blank(**overrides) -> dict:
    row = {k: "" for k in FIELDNAMES}
    row.update(overrides)
    return row


SUMMARY_FIELDNAMES = [
    "model", "provider", "pass_rate", "avg_score", "grade",
    "avg_elapsed_s", "avg_input_tokens", "avg_output_tokens", "errors",
]


def write_csv(results: list[dict], agg: dict[str, dict], output_path: str) -> None:
    with open(output_path, "w", newline="") as f:
        # ── per-case results ──
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in FIELDNAMES})

        f.write("\n")

        # ── model summary ──
        f.write("=== MODEL SUMMARY ===\n")
        summary_writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        summary_writer.writeheader()

        for model in SUPPORTED_MODELS:
            s = agg[model]
            summary_writer.writerow({
                "model": model,
                "provider": s["provider"],
                "pass_rate": s["pass_rate"],
                "avg_score": s["avg_score"],
                "grade": s["grade"],
                "avg_elapsed_s": s["avg_elapsed"],
                "avg_input_tokens": s["avg_input"],
                "avg_output_tokens": s["avg_output"],
                "errors": s["errors"],
            })

        f.write("\n")

        # ── scoring key ──
        f.write("=== SCORING KEY ===\n")
        f.write("40 pts connected | 30 pts contains expected | 20 pts exact match | 10 pts speed rank\n")
        f.write("Grades: A=90-100  B=80-89  C=70-79  D=55-69  F=0-54\n")
        f.write(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# ── main ──────────────────────────────────────────────────────────────────────

async def main_async(concurrency: int, output: str) -> int:
    print("=" * 70)
    print("Model Smoke Test  (async, batched)")
    print("=" * 70)
    print()

    results = await run_all(concurrency=concurrency)
    results = assign_scores(results)
    agg = aggregate_by_model(results)

    # Console summary
    print()
    print("=" * 70)
    print(f"{'Model':<26} {'Pass Rate':>10} {'Avg Score':>10} {'Grade':>6} {'Avg Sec':>9}")
    print("-" * 70)
    for model in SUPPORTED_MODELS:
        s = agg[model]
        print(
            f"{model:<26} {s['pass_rate']:>10} {s['avg_score']:>10.1f}"
            f" {s['grade']:>6} {s['avg_elapsed']:>8.2f}s"
        )
    print("=" * 70)

    write_csv(results, agg, output)
    print(f"\nCSV written → {output}")

    failed_models = [m for m, s in agg.items() if s["passed"] < s["total"]]
    return 1 if failed_models else 0


def main():
    parser = argparse.ArgumentParser(
        description="Async smoke-test all models in batches, output scored CSV."
    )
    parser.add_argument(
        "--output",
        default="model_smoke_test.csv",
        help="CSV output file path (default: model_smoke_test.csv)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=CONCURRENCY_LIMIT,
        help=f"Max simultaneous API calls (default: {CONCURRENCY_LIMIT})",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(main_async(args.concurrency, args.output))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
