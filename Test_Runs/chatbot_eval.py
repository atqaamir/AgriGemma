"""Chatbot evaluation: 35 questions for user 1 on the demo date (32 English + 3 Roman Urdu),
incl. a 5-question conversation from the live app (bare fields, nothing sown yet).

Runs the same streaming pipeline as the chat page (ChatbotService._stream_pipeline) and logs,
per question: detected intent, context size, web search, time per stage, the answer, which
expected facts the answer contains ("facts"), whether the context had them ("in context"),
and "must not say" hits, reported separately as WRONG ADVICE.

Usage (from the project root):
    DEMO_TODAY=2027-05-05 python Test_Runs/chatbot_eval.py --label before --out eval_before.json
    options: --pause 6   seconds between AI calls (rate limits; default 0)
             --only 1,2  run only these question ids
Uses the AI provider from .env (USE_PLACEHOLDER_AI=true for a free dry run). The app start
reseeds the demo database, then the daily update runs once for user 1 (as after a simulator
click): Maize sowing 6 May, Cotton moved to 9 May, Rice Not Feasible.
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATE = r"(?:{d}(?:st|nd|rd|th)?\s+may|may\s+{d}(?:st|nd|rd|th)?)"
day = lambda d: DATE.format(d=d)

# "Must not say" patterns that contradict the plan (reported as WRONG ADVICE). A lookbehind skips
# negated forms ("do not spray", "don't irrigate").
NEG = r"(?<!not )(?<!n't )(?<!never )"
DELAY_MAIZE = [r"delay\w*\s+(?:the\s+)?(?:sowing|planting)[^.]{0,40}maize",
               r"maize[^.]{0,40}\b" + NEG + r"delay\w*\s+(?:the\s+)?(?:sowing|planting)"]
IRRIGATE_NOW = [NEG + r"\b(?:start|begin)\w*\s+(?:the\s+)?irrigat\w*[^.]{0,60}\b(?:immediately|right away|now|today)",
                NEG + r"\birrigate\s+(?:the\s+|your\s+)?maize\s+(?:today|tomorrow|now|immediately)"]
RICE_LATER = [r"\bwait until\b[^.]{0,60}", r"\bsow\w*\s+(?:the\s+)?rice\s+(?:after|later|when|once|on)\b"]
# User 1's fields are bare on the demo date: no plant terms. Style: no "I understand you" openers,
# no "you must".
PLANT_TERMS = [r"\bleaf\b", r"\bleaves\b", r"\bstems?\b", r"\bwilt\w*", r"\bstunted\b", r"\byellowing\b"]
STYLE = [r"\bI understand you", r"\bI know you", r"\byou must\b"]
SOIL = [r"\bsoil\b", r"stubble", r"crust", r"moisture", r"seedbed"]
# Temperatures the forecast does not have (it peaks at 33.5 °C): invented heat.
INVENTED_HEAT = r"\b(?:3[6-9]|4\d)(?:\.\d)?\s*(?:°\s*c|°|degrees)"

# id, question, expected intent(s), facts (each group: list of regex, any may match),
# must-not regexes (wrong advice), follow-up of question id (same conversation)
QUESTIONS = [
    (1, "When should I sow cotton?", ["planting"],
     [[day(9)]],
     [r"sow\w*\s+(?:the\s+|your\s+)?cotton\s+(?:on|by)\s+" + day("[5-8]")], None),
    (2, "Why was my cotton sowing moved?", ["planting"],
     [[day(7), day(8)], [r"sunlight", r"temperature", r"cloud", r"rain", r"shower", r"disturbance", r"weather"]],
     [], None),
    (3, "When will I sow maize?", ["planting"],
     [[day(6), r"tomorrow"]], DELAY_MAIZE, None),
    (4, "Can I grow rice on North Field Alpha?", ["planting"],
     [[r"not feasible", r"not suitable", r"unsuitable", r"sandy", r"not recommended", r"incompatible"]],
     [r"\b(?:yes|you can)\b[^.]{0,40}\b(?:sow|grow|plant)\w*\s+rice"] + RICE_LATER, None),
    (5, "Should I sow rice this week?", ["planting"],
     [[r"not feasible", r"not suitable", r"unsuitable", r"sandy", r"not recommended", r"incompatible"]],
     [r"\b(?:yes|go ahead)\b[^.]{0,40}\brice", r"sow\w*\s+rice\s+(?:on|this|tomorrow|today)"] + RICE_LATER, None),
    (6, "What tasks do I have today?", ["task"],
     [[r"seedbed"], [r"inspection", r"erosion", r"pipe"]], [], None),
    (7, "What is the most urgent task?", ["task"],
     [[r"emergency field inspection", r"soil erosion", r"erosion"]], [], None),
    (8, "What should I do tomorrow?", ["task"],
     [[r"sow\w*\s+(?:the\s+)?maize", r"maize"]], DELAY_MAIZE, None),
    (9, "Do I need to irrigate this week?", ["irrigation"],
     [[day(13), r"not yet", r"no (?:extra )?irrigation", r"after sowing", r"irrigation starts"]],
     IRRIGATE_NOW, None),
    (10, "When does irrigation start for maize?", ["irrigation"],
     [[day(13)]], IRRIGATE_NOW, None),
    (11, "Is it going to rain this week?", ["weather"],
     [[day(7), day(8), r"shower", r"thunder", r"disturbance", r"\brain"]], [], None),
    (12, "How hot will it be this week?", ["weather"],
     [[r"\b3[0-4](?:\.\d)?\s*°?\s*c", r"\b3[0-4](?:\.\d)? degrees", r"\b3[0-4](?:\.\d)?°"]], [], None),
    (13, "Is the weather good for sowing cotton on 8 May?", ["planting", "weather"],
     [[r"\bno\b", r"\bnot\b", r"unsuitable"]], [r"^\s*yes\b"], None),
    (14, "When should I fertilize maize?", ["fertilization"],
     [[day(21)]], [], None),
    (15, "When will my cotton be ready to harvest?", ["harvest"],
     [[r"october", r"\boct\b"]], [], None),
    (16, "How is the soil on The Reservoir?", ["soil"],
     [[r"loam", r"55"]], [], None),
    (17, "Which field has a problem?", ["alert", "general", "soil"],
     [[r"punjab wheat belt"]], [], None),
    (18, "What is the soil moisture on Punjab Wheat Belt?", ["soil"],
     [[r"\b55\b"]], [], None),
    (19, "Which crops am I planning this season?", ["planting", "general"],
     [[r"maize"], [r"cotton"]], [r"rice[^.]{0,30}\b(?:is|are) (?:planned|scheduled)"], None),
    (20, "Why did my plan change today?", ["general", "planting", "weather"],
     [[r"cotton"], [day(9), r"moved", r"delay", r"postpon", r"later"]], [], None),
    (21, "Is my maize healthy?", ["general", "planting"],
     [[r"not (?:yet )?sown", r"before sowing", r"planned", day(6), r"tomorrow", r"not planted"]],
     [r"\bflowering\b", r"\bvegetative\b", r"maize[^.]{0,60}\b(?:under|is in|in an?)\s+[^.]{0,20}(?:stress|alert)"], None),
    (22, "What is the price of cotton seed?", ["general"],
     [], [], None),
    (23, "Hello", ["greeting"], [], [], None),
    (24, "Should I spray fungicide on my cotton?", ["general", "planting", "alert"],
     [[r"not (?:yet )?sown", r"before sowing", r"no need", r"\bno\b", r"not (?:been )?planted"]],
     [NEG + r"\bspray\w*\s+(?:the\s+)?fungicide\s+(?:today|now|tomorrow)"], None),
    (25, "And maize?", ["planting", "general"],
     [[day(6), r"tomorrow"]], DELAY_MAIZE, 1),
    # Roman Urdu
    (26, "kapas kab boni chahiye?", ["planting"],
     [[day(9), r"\b9\b"]], [r"sow\w*\s+(?:the\s+)?cotton\s+(?:on|by)\s+" + day("[5-8]")], None),
    (27, "aaj kya kaam hai?", ["task"],
     [[r"seedbed", r"inspection", r"erosion", r"pipe"]], [], None),
    (28, "is hafte garmi hogi?", ["weather"],
     [[r"\b3[0-4]", r"garm", r"hot"]], [], None),
    # Live-app conversation (verbatim, 16 Nov): fields are bare, nothing is sown yet
    (29, "My crops look unhealthy — what could be wrong?", ["general", "alert", "soil"],
     [[r"not (?:yet )?sown", r"no crops?\b", r"bare", r"not (?:yet )?planted", r"before sowing", r"planned"],
      [r"\bsoil\b", r"seedbed", r"prepar"]], PLANT_TERMS + STYLE, None),
    (30, "whats an emergency field inspection?", ["general", "alert"],
     [[r"(?:not|isn'?t|is not) (?:on|in) your (?:task )?list", r"check(?:ing)? (?:the )?soil before sowing"]],
     PLANT_TERMS + STYLE, 29),
    (31, "what happens in it", ["general", "alert", "soil"],
     [SOIL], PLANT_TERMS + STYLE, 30),
    (32, "why should i do it?", ["general", "alert", "soil"],
     [SOIL, [r"sow", r"maize", r"seed"]], PLANT_TERMS + STYLE, 31),
    (33, "what else should I do today", ["task", "general"],
     [[r"seedbed"], [r"erosion", r"pipe", r"soil"]], PLANT_TERMS + STYLE, 32),
    # Single questions: alert reason; stress and disease risk must not be mixed
    (34, "Why is Punjab Wheat Belt on alert?", ["alert", "general", "soil"],
     [[r"stubble", r"crust", r"\bsoil\b", r"seedbed"]], PLANT_TERMS + STYLE, None),
    (35, "Is The Reservoir at high risk?", ["general", "alert", "soil"],
     [[r"erosion"], [r"(?:stress|disease)[^.]{0,40}\blow\b", r"\blow\b[^.]{0,40}(?:stress|disease)"]],
     PLANT_TERMS + STYLE + [r"(?<!not )(?<!no )\bhigh\b[^.]{0,30}\b(?:stress|disease)",
                            r"\bstress\b[^.]{0,30}\bhigh\b"], None),
]


def _hits(patterns, text):
    return [p for p in patterns if re.search(p, text, re.IGNORECASE | re.MULTILINE)]


def score(qid, answer, context=""):
    """facts_ok, facts_in_context, wrong-advice hits, invented heat for one answer."""
    q = next(x for x in QUESTIONS if x[0] == qid)
    facts, must_not = q[3], q[4]
    return {
        "facts_ok": sum(bool(_hits(g, answer)) for g in facts),
        "facts_in_context": sum(bool(_hits(g, context)) for g in facts) if context else None,
        "wrong_advice": _hits(must_not, answer),
        "invented_heat": bool(re.search(INVENTED_HEAT, answer, re.IGNORECASE)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pause", type=float, default=0.0)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = {int(x) for x in args.only.split(",") if x.strip()}

    logging.disable(logging.CRITICAL)
    import run                                                     # noqa: F401  reseed
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.services.ai_model_service import ai_model_service
    from app.services.intelligence_service.chatbot_service import chatbot_service as cs
    from app.utils import clock

    captured = {}
    _orig_format = cs._format_farmer_context

    def _capture(context, user_message, intent_result):
        s = _orig_format(context, user_message, intent_result)
        captured["context"] = s
        return s
    cs._format_farmer_context = _capture

    rows = []
    with run.app.app_context():
        from app.services import demo_scenario_service
        demo_scenario_service.apply(1, "typical")   # scenario 1: 7–8 May western disturbance
        CoordinatorAgent().daily_update(user_id=1, as_of_date=clock.today())
        provider = ai_model_service.get_provider().name
        print(f"chatbot eval '{args.label}': demo date {clock.today()}, provider {provider}, pause {args.pause}s")
        conv_of = {}
        for qid, question, intents, facts, must_not, follow in QUESTIONS:
            if only and qid not in only:
                continue
            conv = conv_of.get(follow) if follow else None
            conv = cs.ChatbotService.get_or_create_conversation(1, conv)
            conv_of[qid] = conv
            captured.clear()
            t0 = time.time()
            final, stages, error = {}, [], None
            for chunk in cs.ChatbotService._stream_pipeline(1, conv, question, "en"):
                event = re.search(r"^event: (\w+)", chunk, re.M).group(1)
                data = json.loads(re.search(r"^data: (.*)$", chunk, re.M).group(1))
                if event == "status":
                    stages = data.get("stages_log", stages)
                    if data.get("intents"):
                        final["intents"] = data["intents"]
                elif event == "response":
                    final.update(data)
                elif event == "error":
                    error = data.get("message")
            wall = time.time() - t0
            answer = final.get("bot_message") or ""
            context = captured.get("context", "")
            meta = final.get("metadata") or {}
            got_intent = (final.get("intents") or ["?"])[0]
            sc = score(qid, answer, context)
            wrong = sc["wrong_advice"]
            web = [s for s in stages if s.get("stage", "").startswith(("searching_web", "web"))]
            row = {
                "id": qid, "question": question, "expected_intents": intents, "intent": got_intent,
                "intent_ok": got_intent in intents, "facts_total": len(facts), "facts_ok": sc["facts_ok"],
                "facts_in_context": sc["facts_in_context"] or 0, "wrong_advice": wrong,
                "invented_heat": sc["invented_heat"], "web_search": bool(web),
                "fallback": bool(meta.get("is_fallback")), "model": meta.get("model"),
                "total_ms": final.get("total_ms") or round(wall * 1000), "stage_ms": meta.get("stage_ms"),
                "stages": [(s.get("stage"), s.get("elapsed_ms")) for s in stages],
                "context_chars": len(context), "context": context, "answer": answer, "error": error,
            }
            rows.append(row)
            print(f"[{qid:2}] {'✓' if row['intent_ok'] else '✗'} intent {got_intent:13} facts {row['facts_ok']}/{row['facts_total']} "
                  f"(ctx {row['facts_in_context']}/{row['facts_total']})  {'WRONG ' + str(wrong) if wrong else ''}"
                  f"{' web' if row['web_search'] else ''}{' FALLBACK' if row['fallback'] else ''}"
                  f"  {row['total_ms'] / 1000:.1f}s  {question}")
            print(f"       → {answer[:220].replace(chr(10), ' ')}")
            if args.pause and qid != QUESTIONS[-1][0]:
                time.sleep(args.pause)

    n = len(rows)
    facts_total = sum(r["facts_total"] for r in rows)
    summary = {
        "label": args.label, "questions": n,
        "intent_ok": sum(r["intent_ok"] for r in rows),
        "facts_ok": sum(r["facts_ok"] for r in rows), "facts_total": facts_total,
        "facts_in_context": sum(r["facts_in_context"] for r in rows),
        "wrong_advice": [(r["id"], r["wrong_advice"]) for r in rows if r["wrong_advice"]],
        "invented_heat": [r["id"] for r in rows if r["invented_heat"]],
        "web_searches": sum(r["web_search"] for r in rows),
        "fallbacks": sum(r["fallback"] for r in rows),
        "median_s": sorted(r["total_ms"] for r in rows)[n // 2] / 1000 if n else 0,
        "max_s": max((r["total_ms"] for r in rows), default=0) / 1000,
    }
    print("\nSUMMARY", json.dumps(summary, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")


if __name__ == "__main__":
    main()
