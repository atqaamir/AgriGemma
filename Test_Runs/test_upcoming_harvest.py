"""Upcoming Harvest card data: effective harvest dates from the plan (no hard-coded window).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_upcoming_harvest.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402  bootstrap(): reseed + startup forecast (calm: cotton 7 May)

with app.app_context():
    from app.extensions import db
    from app.models.seasonal_plan import SeasonalPlan

    client = app.test_client()
    print("\n-- user 1 at startup: as planned")
    d0 = client.get("/mytasks/1/upcoming-harvest").get_json()
    check({c["crop"]: (c["harvest"], c["moved"]) for c in d0["crops"]} ==
          {"Maize": ("2027-10-06", False), "Cotton": ("2027-10-07", False)}, f"Maize 6 Oct, Cotton 7 Oct: {d0}")
    r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": "typical"})
    check(r.status_code == 200, f"scenario 1 ran ({r.status_code})")
    print("\n-- user 1 on 5 May 2027 (after scenario 1)")
    data = client.get("/mytasks/1/upcoming-harvest").get_json()
    crops = {c["crop"]: c for c in data["crops"]}
    print("    ", data)
    check(set(crops) == {"Maize", "Cotton"}, "feasible crops only (Rice Not Feasible is left out)")
    check(crops["Maize"]["harvest"] == "2027-10-06" and not crops["Maize"]["moved"], "Maize 6 Oct, as planned")
    check(crops["Cotton"]["harvest"] == "2027-10-09" and crops["Cotton"]["moved"]
          and crops["Cotton"]["planned"] == "2027-10-07", "Cotton 9 Oct, moved from 7 Oct with its sowing")
    check(data["earliest"] == "2027-10-06" and data["latest"] == "2027-10-09", "window 6–9 Oct")
    check(crops["Cotton"]["field"] == "The Reservoir" and crops["Maize"]["field"] == "Punjab Wheat Belt",
          "field names")

    for uid in (2, 3):
        d = client.get(f"/mytasks/{uid}/upcoming-harvest").get_json()
        check(isinstance(d["crops"], list), f"user {uid}: {[(c['crop'], c['harvest']) for c in d['crops']]}")

    print("\n-- no feasible crop → empty (card hidden)")
    plan = SeasonalPlan.query.filter_by(user_id=1, currently_active=True).first()
    saved = {e.id: e.feasibility for e in plan.entries}
    for e in plan.entries:
        e.feasibility = "Not Feasible"
    db.session.commit()
    d = client.get("/mytasks/1/upcoming-harvest").get_json()
    check(d == {"crops": [], "earliest": None, "latest": None}, "empty list, no window")
    for e in plan.entries:
        e.feasibility = saved[e.id]
    db.session.commit()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
