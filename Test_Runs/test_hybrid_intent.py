"""Hybrid intent: keywords first, the AI only for keyword misses / uncertain results – no AI,
placeholder provider (the AI call is replaced by fixed / failing / slow stand-ins).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_hybrid_intent.py
Checks: the 40 existing eval questions keep their keyword intent and never call the AI; the 8
keyword misses call it once each; a valid label is used; an invalid label, an error, a timeout
(3 s) or no AI provider give GENERAL; the chatbot pipeline uses the hybrid result.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


def eval_questions():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_eval.py"), encoding="utf-8").read()
    start, end = src.index("DATE = r"), src.index("\n]\n", src.index("QUESTIONS = [")) + 3
    ns = {}
    exec("import re\n" + src[start:end], ns)
    return ns["QUESTIONS"]


from run import app  # noqa: E402

with app.app_context():
    from app.services.intelligence_service.intent import hybrid_intent as hy
    from app.services.intelligence_service.intent.intent_classifier import FarmIntent, IntentResult, classify

    Q = eval_questions()
    old = [q for q in Q if q[0] <= 40 or q[0] > 48]   # keyword questions (incl. 49: scenario 3 decision)
    new = [q for q in Q if 41 <= q[0] <= 48]          # the 8 keyword misses
    check(len(old) == 41 and len(new) == 8, f"41 keyword questions + 8 keyword misses ({len(old)}, {len(new)})")

    calls = []
    orig_ask = hy._ask_ai

    def answer_expected(message):
        calls.append(message)
        q = next(q for q in Q if q[1] == message)
        return q[2][0]

    hy._ask_ai = answer_expected

    print("\n-- the 40 existing eval questions: keyword intent, no AI call")
    hy.reset_stats()
    for qid, text, intents, *_ in old:
        r = hy.classify_hybrid(text)
        kw = classify(text)
        if r != kw or r.primary.value not in intents:
            check(False, f"[{qid}] {text!r}: {r.primary.value} (keywords {kw.primary.value})")
    check(not calls and hy.stats()["calls"] == 0, f"0 AI calls for the 41 ({len(calls)})")
    check(all(classify(q[1]).primary.value in q[2] for q in old), "all 41 keep an expected intent")

    print("\n-- the 8 keyword misses: one AI call each, its label is used")
    for qid, text, intents, *_ in new:
        kw = classify(text)
        r = hy.classify_hybrid(text)
        check(kw.primary == FarmIntent.GENERAL and kw.confidence == 0.0 and r.method == "ai"
              and r.primary.value == intents[0], f"[{qid}] {text!r}: keywords general 0.00 → AI {r.primary.value}")
    check(len(calls) == 8 and hy.stats()["ai_ok"] == 8, f"8 AI calls ({len(calls)})")

    print("\n-- explicit general questions / follow-ups need no AI")
    for text in ("Is my maize healthy?", "What is the price of cotton seed?", "And maize?", "why should i do it?",
                 "Is The Reservoir at high risk?"):
        r = classify(text)
        check(r.primary == FarmIntent.GENERAL and r.confidence == 1.0 and not hy.needs_ai(r), f"{text!r}: general, no AI")
    check(not hy.needs_ai(classify("When should I sow cotton?")), "a confident keyword match: no AI")

    print("\n-- uncertain keyword result (confidence < 0.5) asks the AI")
    tie = IntentResult(primary=FarmIntent.SOIL, secondary=[FarmIntent.IRRIGATION, FarmIntent.WEATHER],
                       confidence=0.4, method="keyword")
    check(hy.needs_ai(tie), "confidence 0.40 → AI")
    check(not hy.needs_ai(IntentResult(FarmIntent.PLANTING, [FarmIntent.WEATHER], 0.55, "keyword")),
          "confidence 0.55 (the lowest eval question) → no AI")

    print("\n-- failures → GENERAL")
    msg = "kab bijai karun?"
    for name, fn in (("invalid label", lambda m: "sowing-ish"), ("empty", lambda m: ""), ("None", lambda m: None),
                     ("error", lambda m: (_ for _ in ()).throw(RuntimeError("503")))):
        hy._ask_ai = fn
        r = hy.classify_hybrid(msg)
        check(r.primary == FarmIntent.GENERAL and r.method == "ai-failed", f"{name} → general")
    hy._ask_ai = lambda m: (time.sleep(5), "planting")[1]
    t0 = time.monotonic()
    r = hy.classify_hybrid(msg)
    dt = time.monotonic() - t0
    check(r.primary == FarmIntent.GENERAL and dt < 3.6, f"slow AI (5 s) → general after {dt:.1f} s (limit 3 s)")
    hy._ask_ai = orig_ask
    t0 = time.monotonic()
    r = hy.classify_hybrid(msg)
    check(r.primary == FarmIntent.GENERAL and time.monotonic() - t0 < 0.5, "placeholder provider (no AI) → general at once")

    print("\n-- the chatbot pipeline uses the hybrid intent")
    hy._ask_ai = lambda m: "harvest"
    from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService
    conv = ChatbotService.get_or_create_conversation(1)
    events = "".join(ChatbotService._stream_pipeline(1, conv, "kapas ki chunai kab karni hai?"))
    m = re.search(r'"intents":\s*\[([^\]]*)\]', events)
    check(m and '"harvest"' in m.group(1), f"stream reports intent harvest ({m.group(1) if m else None})")
    hy._ask_ai = orig_ask

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
