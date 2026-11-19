"""AI text guard + change-notification text – no AI, placeholder provider.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_ai_text_guard.py
Uses the exact texts from the live test of 0c4f87b: notification 5 (a leaked Gemma draft that
names "Wheat") and notification 6 (a cheerful text in the unusual-rain scenario).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


LEAKED_DRAFT = """* User: Ahmad Khan.
* Role: Farm Advisor.
* Context: North Field Alpha, The Reservoir, Punjab Wheat Belt.
* Current Weather: 31.5°C, 0mm rainfall.
* Plan Adjustments:
 * Wheat/Sowing Window 1: Sowing on 6 May is suitable (30-40°C).
 * Maize/Rainfall: Rainfall <50mm means no extra irrigation this week; irrigation starts 13 May. Monitor seed-zone moisture at 5cm depth daily.
 * Sowing Window 2: 7 May and 8 May are unsuitable (too cool/low sunlight). Sowing moved to 9 May (30-40°C and >8h sunlight).
* Constraints:
 * 2-3 friendly sentences.
 * Explain why the week looks different and what to expect.
 * Tone: Warm, friendly, "today is still fine".
 * No bullet points.

 * *Attempt 1 (Mental Draft):* Hi Ahmad Khan, things are looking okay today, but the week ahead has some shifts. We're sticking to the May 6 sowing date for the first batch, but for the second, we'll wait until May 9 to ensure better sunlight and warmth. Also, since rain is low, we'll hold off on extra irrigation until May 13 and just keep a close eye on the seed-zone moisture for the maize.

 * *Refining for Tone and Constraints:* The prompt asks for 2-3 sentences. The draft above is 3 sentences but a bit clunky.

 * *Attempt 2 (Closer to final):* Hello Ahmad Khan, today is looking good, but we'll be making a few adjustments this week to get the best results from your crops. We are pushing the second sowing date to May 9 to catch better sunlight and warmth, and since rain is light, we'll hold off on extra irrigation until May 13 while keeping a close eye on the seed-zone moisture.

 * *Checking against constraints:*
 * Directly to Ahmad Khan? Yes.
 * 2-3 sentences? Yes (2 sentences).
 * Explain why week looks different? Yes (sunlight/"""

CHEERFUL_RAIN = ("Hello Ahmad Khan, it is a beautiful day to be out in the fields with the temperature sitting at a "
                 "comfortable 31.5°C. You will notice that the start of this week is a bit too wet for us to begin "
                 "sowing, so we are going to hold off until the 10th of May when the soil conditions and sunshine "
                 "will be perfect for your crop. Everything is looking good for a strong start, so please enjoy "
                 "these next few days of preparation before we get the seeds into the ground later this week.")

GOOD_TYPICAL = ("Ahmad Khan, cotton sowing on The Reservoir moved from 7 May to 9 May, because 7 and 8 May are too "
                "cool with too little sun. Maize on Punjab Wheat Belt stays on 6 May.")

from app.utils import ai_text_guard as g  # noqa: E402

print("\n-- guard rules (no DB)")
scope = {"allowed_crops": {"Maize", "Cotton"}, "known_crops": {"Maize", "Cotton", "Rice", "Wheat"},
         "not_feasible_crops": {"Rice"}, "field_names": ["North Field Alpha", "The Reservoir", "Punjab Wheat Belt"]}
p = g.problem(LEAKED_DRAFT, **scope)
check(p and "leaked draft" in p, f"notification 5 (live): rejected as a leaked draft ({p})")
for frag in ("* User: Ahmad Khan.\n* Role: Farm Advisor.", " * *Attempt 1 (Mental Draft):* Hi Ahmad",
             "Some text.\n * *Checking against constraints:*", " * 2-3 sentences? Yes (2 sentences)."):
    check(g.draft_problem(frag), f"draft fragment rejected: {frag.strip()[:40]!r}")
last = LEAKED_DRAFT.split("*Attempt 2 (Closer to final):*")[1].split("\n")[0]
p = g.problem("We are pushing the Wheat sowing to 9 May.", **scope)
check(p and "wheat" in p.lower(), f"crop the user doesn't have (Wheat) rejected ({p})")
check(g.problem("Rice on North Field Alpha needs water.", **scope), "Not Feasible crop (Rice) named as grown: rejected")
check(g.problem("Rice is not feasible this season. Cotton moves to 9 May.", **scope) is None,
      "Not Feasible crop (Rice) named as not feasible: passes")
check(g.problem(GOOD_TYPICAL, **scope) is None, "good text with the field 'Punjab Wheat Belt' passes")
check(g.problem("We will attempt to sow on 9 May; the draft plan is ready.", **scope) is None,
      "'attempt' / 'draft' in a normal sentence pass")
check(g.problem("You must sow today.", **scope), "'you must' rejected")
p = g.problem(CHEERFUL_RAIN, verdict="unusual", **scope)
check(p and "cheerful" in p, f"notification 6 (live) in unusual rain: rejected ({p})")
check(g.problem(CHEERFUL_RAIN, verdict="typical", **scope) is None, "same text not rejected for tone when typical")
check(g.problem("Cotton moves to 12 May.", allowed_dates={(9, 5), (7, 5)}, **scope),
      "date not in the facts rejected")

from run import app  # noqa: E402  bootstrap(): reseed + calm startup forecast

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.notification import Notification
    from app.services import change_notification_text as cnt
    from app.services import demo_scenario_service as scenarios
    from app.services.demo_reset_service import reset_demo
    from app.services.intelligence_service.chatbot_service.fallback_answer import CLOSING
    from app.utils import clock

    today = clock.today()

    def run(scenario, ai_answer):
        reset_demo()
        cnt._call_ai = lambda prompt: ai_answer
        before = Notification.query.order_by(Notification.id.desc()).first()
        start = before.id if before else 0
        scenarios.apply(1, scenario)
        CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
        new = Notification.query.filter(Notification.user_id == 1, Notification.id > start).all()
        change = [n for n in new if n.notification_type == "change"]
        alert = [n for n in new if n.notification_type in ("alert", "warning")]
        summary = json.loads(change[-1].detail)["ai_summary"] if change else None
        return summary, (alert[-1].detail if alert else None)

    print("\n-- typical weather, the AI returns the live draft (notification 5)")
    summary, alert = run("typical", LEAKED_DRAFT)
    print("    " + (summary or "-"))
    check(summary and "Attempt" not in summary and "User:" not in summary and "Wheat/" not in summary,
          "pop-up summary: no draft")
    check(summary and "Cotton (The Reservoir): sowing moved from 7 May to 9 May" in summary
          and summary.endswith(CLOSING), "pop-up summary: rule-based text (cotton 7 → 9 May, closing line)")
    check(summary and "within the usual range for early May" in summary, "rule text: typical for the season")
    check(alert == summary, "alert detail: the same rule-based text")

    print("\n-- typical weather, the AI returns a good text")
    summary, alert = run("typical", GOOD_TYPICAL)
    check(summary == GOOD_TYPICAL and alert == GOOD_TYPICAL, "good AI text is shown as it is")

    print("\n-- unusual heavy rain, the AI returns the live cheerful text (notification 6)")
    summary, alert = run("heavy_rain", CHEERFUL_RAIN)
    print("    " + (summary or "-"))
    check(summary and "beautiful" not in summary and "Everything is looking good" not in summary,
          "pop-up summary: no cheerful text")
    check(summary and "unusual for May" in summary and "sowing moved from 6 May to 10 May" in summary
          and "sowing moved from 7 May to 10 May" in summary, "rule text: unusual rain + maize/cotton to 10 May")
    check(alert == summary, "alert detail: the same rule-based text")

    print("\n-- the AI is down (None): rule-based text")
    summary, _ = run("heavy_rain", None)
    check(summary and summary.endswith(CLOSING), "no AI answer → rule-based text")
    reset_demo()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
