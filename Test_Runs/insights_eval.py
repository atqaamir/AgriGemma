"""Eval: task insights + farm report on the demo date with the real AI (Step G.6).

Run from the project root (real provider from .env, NOT the placeholder):
    DEMO_TODAY=2027-05-05 python Test_Runs/insights_eval.py [--task-runs 3]
Reseeds the local DB, runs the simulator's daily update for user 1, then generates task
insights N times (same data) and the farm report once. Writes eval_results/insights_eval_<timestamp>.json
and prints a summary.

Expected links (a case is FOUND when a shown insight cites the case's signal AND its text
names the case's words; FOUND-BUT-DROPPED when only a dropped insight did):
  erosion_cotton – erosion on The Reservoir before the cotton sowing (dependency signal)
  showers_soil   – showers 7–8 May vs soil work (rain signal)
  maize_seedbed  – maize sowing tomorrow vs today's seedbed / soil check (deadline signal)
  rice_nf        – Rice Not Feasible, no tasks (not-feasible signal; farm report)
Every shown text is also checked against the chatbot eval's "must not say" patterns.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Test_Runs.chatbot_eval import (  # noqa: E402
    DELAY_MAIZE, INVENTED_HEAT, IRRIGATE_NOW, PLANT_TERMS, RICE_LATER, STYLE)

MUST_NOT = {"wrong advice: delay maize": DELAY_MAIZE, "wrong advice: irrigate now": IRRIGATE_NOW,
            "wrong advice: rice later": RICE_LATER, "plant terms (all fields bare)": PLANT_TERMS,
            "style (I understand / I know / you must)": STYLE, "invented heat (≥36 °C)": [INVENTED_HEAT]}

CASES = {
    "erosion_cotton": ("dependency:", [r"erosion"], [r"cotton"]),
    "showers_soil":   ("weather:rain:", [r"shower|rain"], [r"soil|seedbed|erosion"]),
    "maize_seedbed":  ("deadline:", [r"maize"], [r"seedbed|soil"]),
    "rice_nf":        ("plan:not_feasible:", [r"rice"], [r"feasib|cannot|not suit|incompatib"]),
}


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def case_ids(signals, prefix):
    return {s["id"] for s in signals if s["key"].startswith(prefix)}


def score_cases(insights, dropped, signals, cases, basic=False):
    if basic:      # rule-based cards are not the AI's result
        return {name: "AI not available" for name in cases}
    out = {}
    for name in cases:
        prefix, words_a, words_b = CASES[name]
        ids = case_ids(signals, prefix)

        def hit(item):
            text = " ".join(str(item.get(k) or "") for k in ("title", "explanation", "recommendation", "text"))
            ev = {str(e).strip("[] ").upper() for e in (item.get("evidence") or [])}
            return bool(ev & ids) and _any(words_a, text) and _any(words_b, text)
        if not ids:
            out[name] = "no signal"
        elif any(hit(i) for i in insights):
            out[name] = "found"
        elif any(isinstance(d["item"], dict) and hit(d["item"]) for d in dropped):
            out[name] = "found but dropped"
        else:
            out[name] = "missing"
    return out


def must_not_hits(texts):
    hits = []
    for label, pats in MUST_NOT.items():
        for t in texts:
            for p in pats:
                m = re.search(p, t, re.I)
                if m:
                    hits.append({"check": label, "match": m.group(0), "text": t[:200]})
    return hits


def raw_evidence(raw, signal_ids, sections=("insights", "watch")):
    """From the raw AI JSON: how many items cite only known ids."""
    from app.utils.ai_json import parse_json_object
    from app.services.insight_validation import evidence_ids
    obj = parse_json_object(raw) or {}
    items = [i for s in sections for i in (obj.get(s) or []) if isinstance(i, dict)]
    valid = sum(1 for i in items if evidence_ids(i.get("evidence")) and
                all(e in signal_ids for e in evidence_ids(i.get("evidence"))))
    return {"items": len(items), "valid_evidence": valid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-runs", type=int, default=3)
    args = ap.parse_args()
    if os.getenv("USE_PLACEHOLDER_AI", "").lower() == "true":
        sys.exit("This eval needs the real AI: unset USE_PLACEHOLDER_AI.")

    from run import app  # bootstrap(): fresh reseed
    with app.app_context():
        from app.agents.coordinator_agent import CoordinatorAgent
        from app.services import farm_report_service, task_insights_service
        from app.services.ai_model_service import ai_model_service
        from app.utils import clock

        today = clock.today()
        CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
        model = ai_model_service.fast_provider_name()
        print(f"\nInsights eval — user 1 on {today} — {model}")
        results = {"date": today.isoformat(), "model": model, "task_insights": [], "farm_report": None}

        for n in range(1, args.task_runs + 1):
            t0 = time.monotonic()
            p = task_insights_service.generate(1)
            wall = round((time.monotonic() - t0) * 1000)
            d, signals = p["data"], p["signals"]
            texts = [x["reason"] for x in d["priority_order"] if x["source"] == "ai"] + \
                    [f"{i['title']}. {i['explanation']} {i['recommendation']}" for i in d["insights"]] + \
                    [w["text"] for w in d["watch"]]
            run = {
                "run": n, "latency_ms": p["latency_ms"], "wall_ms": wall, "basic_summary": d["basic_summary"],
                "error": d["error"],
                "cases": score_cases(d["insights"] + d["watch"], d["dropped"], signals,
                                     ("erosion_cotton", "showers_soil", "maize_seedbed"), d["basic_summary"]),
                "insights": [{"title": i["title"], "evidence": i["evidence"]} for i in d["insights"]],
                "watch": [{"text": w["text"], "evidence": w["evidence"]} for w in d["watch"]],
                "priority_order": [f"#{x['task_id']} {x['title']} ({x['source']}): {x['reason']}"
                                   for x in d["priority_order"]],
                "dropped": [{"section": x["section"], "reason": x["reason"]} for x in d["dropped"]],
                "raw_evidence": raw_evidence(d.get("raw_answer"), {s["id"] for s in signals}),
                "must_not": must_not_hits(texts),
                "uses_must": [t[:120] for t in texts if re.search(r"\bmust\b", t, re.I)],
            }
            results["task_insights"].append(run)
            found = sum(v == "found" for v in run["cases"].values())
            print(f"  task insights run {n}: {found}/3 links {run['cases']} | {run['latency_ms']} ms | "
                  f"{len(run['insights'])} insights, {len(run['dropped'])} dropped | must-not {len(run['must_not'])}"
                  + (f" | BASIC SUMMARY ({run['error']})" if run["basic_summary"] else ""))

        t0 = time.monotonic()
        p = farm_report_service.generate(1)
        wall = round((time.monotonic() - t0) * 1000)
        d, signals = p["data"], p["signals"]
        texts = [d["headline"]] + [v for k, v in d["sections"].items() if d["section_source"][k] == "ai"] + \
                [f"{i['title']}. {i['explanation']} {i['recommendation']}" for i in d["insights"]]
        rep = {
            "latency_ms": p["latency_ms"], "wall_ms": wall, "basic_summary": d["basic_summary"], "error": d["error"],
            "cases": score_cases(d["insights"], d["dropped"], signals, tuple(CASES), d["basic_summary"]),
            "headline": d["headline"], "sections": d["sections"], "section_source": d["section_source"],
            "insights": [{"title": i["title"], "explanation": i["explanation"], "evidence": i["evidence"]}
                         for i in d["insights"]],
            "dropped": [{"section": x["section"], "reason": x["reason"]} for x in d["dropped"]],
            "raw_evidence": raw_evidence(d.get("raw_answer"), {s["id"] for s in signals}, ("insights",)),
            "must_not": must_not_hits(texts),
            "uses_must": [t[:120] for t in texts if re.search(r"\bmust\b", t, re.I)],
        }
        results["farm_report"] = rep
        found = sum(v == "found" for v in rep["cases"].values())
        print(f"  farm report: {found}/4 cases {rep['cases']} | {rep['latency_ms']} ms | "
              f"{len(rep['insights'])} insights, {len(rep['dropped'])} dropped, sections from rules: "
              f"{[k for k, v in rep['section_source'].items() if v == 'rule']} | must-not {len(rep['must_not'])}"
              + (f" | BASIC SUMMARY ({rep['error']})" if rep["basic_summary"] else ""))

        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = ROOT / "eval_results" / f"insights_eval_{stamp}.json"   # one file per run, nothing overwritten
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nWritten: {out}")


if __name__ == "__main__":
    main()
