"""Chatbot rule-based answer (both AI models down) – no AI, placeholder provider.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_chat_fallback.py
Forces the fallback (every chat AI call returns "not available") and runs the eval questions
Q36–40 through the real chat pipeline in both scenarios, plus a task and a general question.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402  bootstrap(): reseed + calm startup forecast

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.services import demo_scenario_service as scenarios
    from app.services.ai_model_service import ai_model_service
    from app.services.intelligence_service.chatbot_service import chatbot_service as cs
    from app.services.intelligence_service.chatbot_service.fallback_answer import CLOSING, NO_AI
    from app.utils import clock

    DOWN = "The AI advisor is not available right now. Please try again in a moment."
    ai_model_service.chat_stream_complete = lambda prompt: iter([DOWN])
    ai_model_service.chat_complete = lambda prompt, timeout: DOWN
    today = clock.today()

    def ask(question, conv=None):
        conv = cs.ChatbotService.get_or_create_conversation(1, conv)
        final = {}
        for chunk in cs.ChatbotService._stream_pipeline(1, conv, question, "en"):
            event = re.search(r"^event: (\w+)", chunk, re.M).group(1)
            if event == "response":
                final = json.loads(re.search(r"^data: (.*)$", chunk, re.M).group(1))
        meta = final.get("metadata") or {}
        return final.get("bot_message") or "", bool(meta.get("is_fallback")), conv

    def no_rice_active(a):
        return all("Not Feasible" in line for line in a.splitlines() if "Rice" in line) and "active crops" not in a

    def common(a, label):
        check(a.rstrip().endswith(CLOSING), f"{label}: ends with the re-check / decision line")
        check(no_rice_active(a), f"{label}: Rice only as Not Feasible, never as active")
        check(not re.search(r"\byou must\b|\bleaves\b|\bstems?\b", a, re.I), f"{label}: no 'you must', leaves, stems")

    print("\n-- starting state (no forecast change)")
    a, fb, _ = ask("When should I sow cotton?")
    print("    " + a.replace("\n", "\n    "))
    check(fb and "Cotton (The Reservoir): sowing on 7 May, as planned" in a
          and "Maize (Punjab Wheat Belt): sowing on 6 May, as planned" in a, "planting: both as planned")
    check("Rice (North Field Alpha): Not Feasible this season" in a, "Rice named as Not Feasible")
    common(a, "start")

    print("\n-- scenario 1 (typical early-May weather)")
    scenarios.apply(1, "typical")
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    a, fb, _ = ask("Why did my cotton sowing move?")
    print("    " + a.replace("\n", "\n    "))
    check(fb and "Cotton (The Reservoir): sowing moved from 7 May to 9 May: first day in the sowing window with "
          "temperature 30–40 °C and sunlight >8 h (7 May: temperature 20–30 °C, sunlight 4–8 h" in a,
          "Q36: cotton 7 → 9 May with the plan's reason (7–8 May too cool / too little sun)")
    check("Maize (Punjab Wheat Belt): sowing on 6 May, as planned" in a, "Q36: maize unchanged")
    check("within the usual range for early May" in a, "Q36: typical for the season")
    common(a, "Q36")

    print("\n-- scenario 2 (unusual heavy rain): the Q37–40 conversation")
    scenarios.apply(1, "heavy_rain")
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    conv = None
    answers = {}
    for qid, q in ((37, "Why did my maize sowing move?"),
                   (38, "But it never rains this much in May. Why should I trust this?"),
                   (39, "What happens if I sow anyway?"),
                   (40, "Okay, and when should I sow now?")):
        a, fb, conv = ask(q, conv)
        answers[qid] = (a, fb)
        print(f"  Q{qid}: {q}\n    " + a.replace("\n", "\n    "))
        check(fb, f"Q{qid}: rule-based answer")
        common(a, f"Q{qid}")
    maize = ("Maize (Punjab Wheat Belt): sowing moved from 6 May to 10 May: heavy rain on 6–8 May (38, 62 and 45 mm): "
             "the seed bed is waterlogged on 6–9 May (soil moisture >60 %) – waterlogged seed-beds cause seed rot")
    for qid in (37, 39, 40):
        a = answers[qid][0]
        check(maize in a, f"Q{qid}: maize 6 → 10 May, rain 6–8 May with amounts, waterlogged 6–9 May, seed rot")
        check("Cotton (The Reservoir): sowing moved from 7 May to 10 May" in a, f"Q{qid}: cotton 7 → 10 May")
        check("unusual for May: 145 mm of rain in 7 days against the app's normal of 8 mm" in a,
              f"Q{qid}: unusual vs. the app's normal for May")
        check(not re.search(r"\bsow\w*\s+(?:on|by)\s+[678] may", a, re.I), f"Q{qid}: no sowing date in the rain")
    a = answers[38][0]
    check(a.startswith(NO_AI) and "unusual for May" in a and "Maize (Punjab Wheat Belt): sowing moved from 6 May "
          "to 10 May: heavy rain on 6–8 May" in a, "Q38 (general): 'can't reach the AI' + weather facts + sowing")

    print("\n-- task question")
    a, fb, _ = ask("What are my tasks today?")
    print("    " + a.replace("\n", "\n    "))
    lines = [l for l in a.splitlines() if l.startswith("- ")]
    prios = [l.split(" – ")[1].split(",")[0] for l in lines]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    check(fb and lines and all("today" in l or "tomorrow" in l or "overdue" in l for l in lines),
          f"tasks: only today / tomorrow / overdue ({len(lines)} tasks)")
    check(not any("Sow Maize" in l for l in lines), "tasks: no Sow Maize today/tomorrow (moved to 10 May)")
    today_prios = [order[p] for l, p in zip(lines, prios) if "today" in l]
    check(today_prios == sorted(today_prios) and prios and prios[0] == "critical", f"tasks: priority order {prios}")
    common(a, "tasks")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
