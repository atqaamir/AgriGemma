# Assumptions

The following assumptions define the current scope and operational boundaries of the system. These simplifications allow the platform to focus on core climate-adaptive planning functionality without over-engineering edge cases that are outside the current project scope.

---

## Scheduling

- The farming day begins at **5:00 AM** and ends at **7:00 PM** local time.
- Daily tasks are generated one day at a time.
- The weekly plan is a rolling 7-day window starting today.
  - The 5:00 AM daily update regenerates it every morning (today..today+6) from the unchanged seasonal plan, then applies the forecast.
  - The Monday 3:30 AM weekly plan job is still scheduled but now redundant: the daily update already rolls the plan every day.

---

## Farmer Behaviour

- The farmer always completes all assigned tasks.
- The farmer always follows the generated plan and never rejects a proposed change.
  - *Farmer approval workflows are intentionally bypassed in the current implementation.*

---

## Farm Conditions

- There is no crop damage, pest outbreak, weed growth, or disease event in the current system.
- Fertiliser management is not yet supported.
- Crops are always assumed to require irrigation regardless of environmental moisture conditions.
- Each field contains exactly one active crop at a time.
  - Intercropping and staggered crop rotation are not currently supported.
- Crop growth stages are updated manually.
  - The system does not automatically progress crops through lifecycle stages over time.
- Resource constraints are ignored.
  - Labour availability, water limitations, and equipment availability are not considered during planning.
- Tasks are treated as fully independent.
  - Delaying one task does not automatically shift downstream dependent tasks.

---

## Geographic Scope

- The system currently supports only:
  - Lahore
  - Karachi
  - Islamabad
- Users outside these cities are mapped to Lahore by default.
- All fields belonging to a farmer are assumed to exist within the same geographic region.
- Weather is region-based rather than coordinate-based.
  - Two farms within the same city receive identical weather conditions regardless of physical distance.

---

## Weather & Climate Scenarios

- Weather data is evaluated at daily resolution only.
  - Intra-day conditions such as morning dew, afternoon heat peaks, or overnight frost are not modelled.
- Weather changes can only delay tasks.
  - Tasks are never moved earlier than originally scheduled.
- The system currently supports exactly four weather-change scenarios:

| Scenario | Description |
|---|---|
| **A** | No weather change — no action required |
| **B** | Forecast changed, but no impact on planning or tasks |
| **C** | Forecast changed and impacts the weekly plan only |
| **D** | Forecast changed and impacts both the weekly plan and daily tasks |

### Heavy rain and the seed bed (placeholders until an agronomist validates them)

- **Seed bed after heavy rain (R1).** The fields' soil moisture is a stored reading that rain does not change. For the
  sowing-day check, a day with **≥ 20 mm** of forecast rain, and **one drying day** after it, count as a saturated seed
  bed (soil moisture > 60 %). The existing waterlogging rule then decides ("Waterlogged seed-beds cause seed rot …",
  delay sowing). The plan text says "soil moisture >60 % (seed bed after ≥20 mm rain)". 20 mm and the one drying day
  are placeholders (`RuleEngine.SEEDBED_RAIN_MM`, `SEEDBED_DRYING_DAYS`).
- **Rainfall rule on the weekly total (R2).** The rainfall bands (< 50 … > 300 mm) are seasonal amounts (e.g. maize
  "ideal 100–200 mm at sowing"). The weekly rules (dry week, irrigation adjustments) therefore compare the **forecast
  total of the visible days**, not one day's rain – still an approximation of a seasonal amount. The sowing-day check
  keeps per-day values (plus R1), so one rainy day does not block a whole week. The baseline pass at seeding is unchanged.
- Light showers (e.g. 8 mm and 4 mm) do not trigger R1; plans of users without heavy rain are unchanged.

---

## Demo Scenario: Pre-Sowing Decision

- **The rule base covers Kharif crops** (Maize, Rice, Cotton), which are sown roughly April–July.
  Outside that season (e.g. in November) no day is suitable for sowing them, which is the correct answer.
- **The demo runs on a simulated date in the Kharif season** (demo clock):
  - `DEMO_TODAY=YYYY-MM-DD` in the environment (e.g. `2027-05-05`) sets "today" for planning, weather,
    tasks, jobs and seeders. Empty or unset means the real date.
  - Timestamps (created at, job start/end) keep the real time.
  - The UI shows a banner such as "Demo date: 5 May 2027 (Kharif season)" when it is set.
- **Rabi crops** (wheat, chickpea) are a data addition for later: crop and rulebook values validated by an agronomist.
- The demo represents a farmer **planning to sow this week**, not a crop already in the ground.
  - Seeded sowing dates are set relative to today (today to today + 2), so they always fall inside the simulator's week.
  - The demo weather is realistic for early May in Punjab (hot, dry, long sunshine). Nothing in it is hand-picked
    for a crop.
  - **Starting state** (fresh start and "Reset demo"): user 1's forecast equals the baseline, so there is no
    forecast change and the plan is as planned (maize 6 May, cotton 7 May); today's and tomorrow's tasks exist.
  - **Weather Change Simulator scenarios** (dropdown; `app/services/demo_scenario_service.py`). Each writes the full
    7-day forecast for user 1's region (baseline + its days) and runs the complete daily update right away (plan,
    task sync with moves/cancellations, "Why" explanations, notifications, stale banner on insights), as if the
    forecast changed during the day after the 7 PM tasks existed. All changes come from the rules:
    - *Expected change: typical early-May weather* – a western disturbance on 7–8 May (27.5–28 °C, 8 and 4 mm,
      5.5–6 h sun). Cotton moves 7 → 9 May (temperature 20–30 °C, sunlight 4–8 h), with harvest, irrigation start
      and fertilization; maize stays on 6 May. No task moves (plan tasks exist for today and tomorrow only).
    - *Unexpected change: heavy rain, unusual for early May* – thunderstorms with 38, 62 and 45 mm on 6–8 May
      (86–92 % humidity, 1.5–3 h sun, 25.5–27 °C). Waterlogged seed bed (heavy-rain rule above): maize 6 → 10 May,
      cotton 7 → 10 May, with cascades; the Sow Maize task moves to 10 May. A banner shows while it is active.
  - The active scenario is kept in memory (one gunicorn worker); a restart reseeds, so it starts with none.
- The whole seasonal plan uses the growth stage **Sowing**, and so do user 1's crop records.
  - A crop has no planting date until its sowing task is completed; the completion sets the planting date (and the
    harvest date from the crop duration), un-completing clears it. Until then the pages show
    "Planned: <date> (weekly plan)" from the effective sowing date, or "Not Feasible".
  - Every seeded task fits a hot, dry early May and the plan (no tasks for Not Feasible or unsown crops).
  - The rulebook lookups and the seeded demo weather were designed for this stage (e.g. a cold spell → "delay sowing by 4 days").
- **Why not sowing dates in the past?** In real farming, sowing usually happened earlier, and that is valid.
  But a past sowing date combined with the fixed "Sowing" stage would be inconsistent, and sowing-stage rules
  (such as delaying sowing) have nothing to act on once sowing is over.
- **Intended future behaviour:**
  - The farmer enters the actual sowing date per field.
  - The growth stage advances automatically based on days since sowing.
  - The rules for the current stage apply, so mid-season weather triggers stage-specific changes
    (e.g. more irrigation during flowering in a heatwave).

---

## Planned vs Actual Dates (Plan Event Overrides)

- The **seasonal plan holds the planned dates** and is never changed by daily operations.
- **Actual dates** live in a separate layer, `PlanEventOverride`, one row per change of a one-time event
  (sowing, fertilization, harvesting, irrigation start):
  - `forecast_shift`: a forecast rule moved the event (e.g. "Sowing delayed by 4 days — unfavourable sunlight conditions").
    A sowing delay also moves harvest, irrigation start and fertilization by the same number of days.
  - `farmer_completed`: the farmer marked the sowing task done; the actual sowing date is the completion date, and
    harvest, irrigation start and fertilization move by the difference to the previous sowing date (the date the plan
    showed until then, which may already include a forecast shift).
    Un-completing the task removes these rows again.
- The weekly plan is built from **effective dates**: the latest override per event, otherwise the seasonal date.
  Irrigation repeats from the effective irrigation start until the effective harvest date.
- **The farmer beats the forecast:** once sowing is recorded as done, it is no longer an upcoming event and the
  forecast cannot shift it; a later forecast can still move harvest.
- Every override stores the day of the decision (`as_of_date`). When planning for a day, that day's own forecast
  decisions are recalculated, not re-applied, so running the daily update or the simulator twice gives the same result.
- Temporary adjustments (extra or removed irrigation sessions, "avoid this window") are **not** stored; they are
  recalculated every day from the forecast.
- **Extra irrigation sessions** (e.g. a dry week: rainfall <50 mm → "irrigation increase days") are only placed on
  free days from the effective irrigation start up to the day before the effective harvest, never before sowing.
  If no day of the plan window qualifies, the plan says so, e.g. "Dry week: no extra irrigation – irrigation starts
  13 May". Pre-sowing irrigation (rauni) is not modelled yet.
- **Sowing window:** each crop has a sowing window from the planned (seasonal) sowing date to
  planned + `MAX_SOWING_DELAY_DAYS` (14 days, a **placeholder until validated by an agronomist**).
  - Every day the plan picks the **first suitable day** in the window within the visible forecast (today..today+6):
    a day where none of the crop's sowing-stage rules (temperature, humidity, sunlight, rainfall, soil moisture, pH)
    says "delay sowing" or "avoid". Rules don't add up — a day is suitable or not.
  - It is recalculated from scratch every day, so sowing can move **earlier** again when the forecast improves,
    but never before the planned date and never before today.
  - No suitable day in the forecast: sowing is provisionally the first window day after the forecast, with
    "No suitable sowing day in the forecast – re-checked daily".
  - **No suitable day left in the window** (the window end is in the forecast and no remaining day is suitable):
    sowing is **not** scheduled on an unsuitable day. The crop shows "No suitable sowing day left in the sowing
    window – decision needed" with the same options as overdue; it is re-checked daily until the window ends.
  - Harvest, irrigation start and fertilization follow the effective sowing date. A completed sowing (farmer) is never
    moved.
- **Sowing overdue → human decision:** when the window has passed and sowing was not completed, the crop stays in the
  weekly plan as "Sowing overdue – decision needed" (no sowing, irrigation or fertilization events) with the options:
  sow anyway with precautions, switch to a short-duration variety, switch crop, or skip the season. The system does
  not choose. **One notification per crop** (decision needed or overdue, whichever comes first) is sent **on the day it
  happens**, also on days without a plan impact.
- **The daily update always applies the forecast to the weekly plan** (sowing window, actual dates) and then syncs the
  plan tasks (below). Their only AI call is one batched explanation call when plan tasks were created, moved or
  reactivated (0 calls when nothing changed); their only notification is the sowing decision above. Other
  notifications, weather-rule task updates and AI summaries only follow on days with a plan impact (plus the existing
  weather-only notification on "change without impact" days).
- A same-day rebuild without the forecast (weekly job, app restart) shows that day's plan without its forecast
  decisions until the next daily update or simulator run.
- **Demo:** overrides are deleted together with the seasonal plans when the app restarts and reseeds (`run.py`),
  so actual dates do not survive a restart.

---

## Season Lifecycle (next step)

- A seasonal plan covers **one growing cycle**: from its first sowing to its last harvest.
- **Today** a seasonal plan is generated only at app start (seed data) and has no end: it stays active after its last
  harvest, and nothing prepares the next season.
- **Planned next:**
  - each seasonal plan gets a season name with a start and end (e.g. "Kharif 2027", first sowing → last harvest);
  - the plan completes automatically after the last **effective** harvest (actual dates, incl. farmer completions);
  - 4–6 weeks before the next sowing window, a notification asks the farmer which crops to plan for that season.
  - This needs **Rabi crops** (wheat, chickpea) in the rule base first; today it covers Kharif crops only.
- Season months (`SEASON_MONTHS`): Summer Apr–Jun, Rainy Jul–Sep, Fall Oct–Nov (Rabi sowing; the rule base scores
  Rabi best in Fall), Winter Dec–Mar. Every month belongs to exactly one season (`Test_Runs/test_season_months.py`).

---

## Tasks from the Weekly Plan

- **Plan tasks** (`task_category = "plan"`) are created from the weekly plan's events: sowing, irrigation,
  fertilization and harvesting, e.g. "Sow Cotton – The Reservoir".
- **The rules decide the task and its date; the AI only explains it.**
  - The description is deterministic: the plan event plus the rule behind it (sowing window text, "Extra session:
    Dry week: rainfall <50 mm forecast", "Moved from 1 Jun: …" for a rule-shifted fertilization or harvest).
  - The "Why this task" explanation (`ai_explanation`) is written by the AI from the rule facts only (event, crop,
    field, due date, rule text, extra/regular session, the forecast for that day): 1–2 sentences, no other date than
    the due date, no new advice. An explanation that names another date is dropped and logged.
  - When: only for plan tasks that were created, moved or reactivated, in **one batched call per user and run**
    (fast provider, minimal thinking), limited to 8 s. On a failure or timeout the explanation stays empty and the
    task is created as usual; the next run fills it in (pending plan tasks without an explanation, max 10 per
    batch). Without a model (placeholder AI) a fixed text from the rule facts is used.
  - The 7 PM job creates tomorrow's tasks; every daily update (and the Weather Change Simulator) also creates any
    missing tasks for today and tomorrow.
  - A task is linked to its seasonal plan entry, and to a crop + field only when exactly one active crop on an active
    field matches the entry (crop, soil type, water source); otherwise it is created unlinked with a warning.
  - No task for a "Not Feasible" entry or for a sowing that is already recorded as done; never duplicated.
- **Plan tasks follow the plan** after every re-plan:
  - Sowing, fertilization and harvest have one task per entry: when the plan moves the event, the task's due date
    moves; when the event leaves the 7-day window (e.g. no suitable sowing day, decision needed) the task is
    deactivated; when it comes back, the same task is reactivated with the new date. A missed fertilization or
    harvest task (due date passed) is left as it is.
  - **Irrigation tasks are never moved**: an irrigation change is handled as deactivate (dropped date) + create (new
    date), matched by entry, type and date. A date that comes back reactivates its task.
  - Completed tasks are never changed.
- **The weekly plan owns a plan task's due date, type and category**: the API ignores changes to them and the edit form
  shows them read-only ("Set by the weekly plan"). Completing, notes, title, priority and description stay editable.
- Weather-rule task updates (impact-on-tasks days) skip plan tasks (the plan already contains the weather's effect) and
  leave unaffected tasks' priority alone.
- Every task change is recorded in the task's history with the (demo) date (`changed_on`); change notifications report
  only the changes of that day.
- **A deactivated task is "Cancelled", not something to do:** it is left out of every pending list and count (tasks,
  crop and field pages and cards, dashboard) and of the chatbot / AI task context. The "all tasks" view shows it greyed
  out as "Cancelled" with the reason from its history. Completed tasks stay as they are.
- The chatbot, AI and notification context only contain the current user's tasks, fields and crops.

---

## Chatbot

- The chatbot answers from the farm's own data: every question gets the plan (today's date, each crop's field,
  sowing date and reason, irrigation start, fertilization and harvest dates, Not Feasible crops) and the same 7-day
  forecast the weekly plan uses. The plan's dates are authoritative.
- Intents are found by whole-word keywords (English and some Roman Urdu); no AI call for that.
- Web search only for general questions that are not about the farm (e.g. a seed price), with a 3 s limit.
- The last 6 messages of the conversation are passed as history.
- An unusable AI answer (empty, a template, an echo) is retried once; then a rule-based answer is shown.
- **Forecast change vs. the app's climate normal** (`forecast_vs_normal_service`, no AI): when the forecast differs
  from the baseline weather, every question gets a block with the changed days (forecast vs. expected before), the
  7-day forecast against the app's normal for the month (region climate profile), a verdict, today's plan changes
  with the rule reasons (rulebook reasoning texts of the factors that made the skipped sowing days unsuitable) and
  today's task moves/cancellations. Verdict (placeholder thresholds): **unusual** when the 7-day rain is more than
  2× the month's normal rain and at least 20 mm, or the average temperature is 7 °C or more from the month's normal
  mean; otherwise **typical for the season**. Prompt rules: explain from the forecast, the normal and the rule reasons;
  say typical or unusual and compare "with the app's normal for <month>"; "less predictable" is allowed, but no
  statistics or climate-change figures that are not in the data; the farmer decides, the plan re-checks the forecast
  every morning. The climate profiles are approximate monthly values in the app, not an official climatology.
- Evaluation: `Test_Runs/chatbot_eval.py` (28 questions incl. 3 Roman Urdu, expected facts and "must not say" checks).

---

## Task insights and farm report (grounded AI)

- **Signals first, no AI:** `insight_signals_service` turns the farm's data into evidence-backed signals, each with
  an id (S1…) and its sources (task ids, plan events, forecast days, fields): deadlines (an event in 1–2 days + the
  tasks due before it), dependencies (a critical/high field task + a sowing or first irrigation on that field in 3–6
  days), weather windows (rain ≥ 2 mm, average ≥ 36 °C – the thresholds the forecast summary already uses; a dry week
  only when the plan's rainfall rule says so), plan changes (planned vs effective date with the reason and what moved
  with it, sown, decision needed / overdue, Not Feasible), load (high/critical tasks per day, overdue) and field status
  (bare vs sown, scores in words). No new agronomic thresholds.
- **One AI call per button:** "Task insights" (tasks page) and the farm report (dashboard sparkle / "Farm report").
  Opening a stored result never calls the AI. Gemma via Google AI with minimal thinking and temperature 0.1.
- **The AI connects, it does not decide:** it may only connect the given signals, every insight cites signal ids,
  it recommends ("I'd recommend…") and never moves dates or creates tasks.
- **Validation in code** drops an insight with no or unknown evidence, a date not in the signals it cites, "I
  understand / I know / you must", first-person changes ("I've moved…") or leaves/stems on a bare field. The priority
  order is limited to real tasks due today/tomorrow; a farm-report section with a date not in the data falls back to
  its rule text. If the AI fails, times out or returns no JSON, a rule-based **basic summary** is shown (labelled).
- **Staleness:** each result stores the signals and a fingerprint of the demo date, the tasks and the plan. When they
  change the page says "Your farm changed since this report – regenerate?" – no automatic AI call. "What changed" in
  the farm report is a diff of the stored signals, computed in code.
- **Limits:** the validator is strict – an insight that names a date from a signal it did not cite is dropped even if
  the date is right. Google AI sometimes answers HTTP 503 ("high demand") or very slowly; without an answer the page
  shows the basic summary.
- **Fallback model (optional):** `GOOGLE_AI_FALLBACK_MODEL` (e.g. `gemini-3.1-flash-lite`). When the main Gemma model
  answers HTTP 503/429 or times out, the same request is sent once to the fallback model (direct, chat, JSON and
  streaming calls) before giving up; with a fallback set, a 503 goes straight to it instead of retrying the busy model.
  The log says which model answered, and stored insights / reports record it ("… (fallback)"). The fallback is not a
  Gemma model, so answers can differ in style; it is only used when Gemma is unavailable. Empty = no fallback.
- Evaluation: `Test_Runs/insights_eval.py` (real AI, demo date: 3× task insights, 1× farm report, the four expected
  links, dropped items, "must not say" checks, latency); placeholder tests `Test_Runs/test_insight_signals.py`,
  `test_insight_reports.py`, `test_task_insights.py`, `test_farm_report.py`.

---

## Live Demo (Render)

- There is no login. To keep the public demo safe, the admin tools are **off unless `DEMO_ADMIN_ENABLED=true`**
  (unset on Render): Flask-Admin (`/admin`), "Refresh Data" (wipes and reseeds the database) and the AI prompt test
  page (`/test/ai`). Locally, `.env` sets `DEMO_ADMIN_ENABLED=true`.
- The Weather Change Simulator stays public (it is the demo). Each run makes an AI call, so one user can run it at most
  every `SIMULATOR_COOLDOWN_SECONDS` (default 30); a click inside the cooldown gets "Simulator just ran – try again in
  N s" (HTTP 429). The cooldown is kept in memory, which works because the app runs one gunicorn worker.
- **Reset demo** (button next to the simulator, `POST /mytasks/<id>/reset-demo`) is public too, unlike Refresh Data:
  it puts the farm back to the fresh-start state (reseed of the demo tables + the calm startup forecast, no AI, no
  notifications), so the scenarios can be run again. It never touches vocabulary or rulebook tables. One reset per
  60 s for the whole app (HTTP 429 with "try again in N s"); the confirmation is in the page (no browser popup).
  Everyone using the live demo at that moment sees the reset (one shared demo farm).
- `GET /health` returns "ok" for an uptime ping that keeps the free Render instance awake.
- **Keep-alive:** the free Render instance sleeps after 15 minutes without requests (the next request then waits for a
  cold start, which also reseeds the demo). The GitHub Actions workflow `.github/workflows/keep-alive.yml` pings
  `/health` every 10 minutes to keep it awake.
  - GitHub may delay scheduled runs (often by several minutes under load), so the instance can still fall asleep now
    and then.
  - GitHub disables scheduled workflows after 60 days without repository activity; re-enable it under
    Actions → Keep alive.
- `SECRET_KEY` should be set on Render (the app has no sessions yet, so the default is not a risk today).

---

## System Behaviour

- All background jobs are assumed to succeed successfully.
- Retry mechanisms and failure recovery workflows are not currently implemented.
- Change-history requests always return summarised reports for the selected date range.

---

# Known Limitations

---

## Simulated Weather Data

Weather forecasts are currently generated using hardcoded monthly climate profiles rather than a live weather API.

The system simulates realistic climate conditions for the supported regions, but the forecasts are not:
- real-time
- location-accurate
- day-accurate

Future versions will integrate live weather providers such as:
- OpenWeatherMap
- Pakistan Meteorological Department APIs

---

## Geographic Scope — Pakistan Only

The rule base, climate profiles, and agricultural thresholds are calibrated specifically for Pakistani farming conditions.

The current implementation is not intended to generalise globally without:
- regional climate tuning
- updated agricultural rule sets
- localisation adjustments

---

## Wind Speed — Tracked but Not Used

Wind speed data is stored in the system but is not currently used in:
- planning
- risk analysis
- recommendation generation

As a result, the platform does not yet respond to:
- high-wind irrigation inefficiencies
- spraying risks
- wind-induced crop stress

---

## Task Scheduling — Date-Level Only

Tasks are scheduled by date only, not by time-of-day.

This limits the system’s ability to optimise work around:
- peak daytime heat
- ideal irrigation timing
- temperature-sensitive operations

---

## Google AI — HTTP 500 Error

Occasionally, calls to the Gemma model (`gemma-4-26b-a4b-it`) may return HTTP 500 errors.

This is a server-side issue related to the current early-access release of the Gemma 4 Mixture-of-Experts model and its streaming endpoint stability.

The system already handles this gracefully:
- failed streaming requests automatically fall back to standard non-streaming `generateContent` calls
- chatbot functionality continues normally
- responses simply appear all at once instead of streaming token-by-token

Potential long-term fixes include:
- waiting for Google to stabilise the streaming endpoint
- switching permanently to non-streaming responses

---

# Future Work

The following improvements and extensions are planned for future development iterations.

---

## Planning & Intelligence

- Allow farmers to regenerate weekly plans based on unfinished tasks.
- Support advancing tasks earlier when weather conditions require it.
- Allow farmers to:
  - reject
  - negotiate
  - modify
  proposed plan changes.
- Expand change-history tracking into a complete time-series intelligence system.
- Build full audit trails for all planning modifications.

---

## Weather & Climate Intelligence

- Integrate live weather APIs for real-time forecasting.
- Add intra-day weather awareness for:
  - heat-sensitive scheduling
  - optimal irrigation timing
  - safer field operations
- Expand geographic support beyond the current three cities.
- Add wind-speed-aware planning and risk analysis.

---

## Farm Management

- Add full crop growth management including:
  - irrigation scheduling
  - pest management
  - weed control
  - fertilisation
- Add fertiliser and pesticide modules.
- Add advanced soil metrics:
  - pH
  - salinity (EC)
  - sulphur
  - nutrient tracking
- Add environmental irrigation-need checks.
- Build a standardised crop-health classification system.
- Add AI-powered pest detection using image analysis.
- Add crop variety and seed recommendation workflows.
- Expand crop support coverage.

---

## Planning & Task Intelligence

- Automatically advance crop growth stages over time.
- Introduce task dependency chains.
- Model resource constraints including:
  - labour
  - water
  - equipment
- Support multi-region farms with field-specific weather planning.

---

## Rules & Customisation

- Allow farmers to define custom operational rules.
- Add automated rule-engine update workflows.
- Migrate the intelligence layer toward a RAG (Retrieval-Augmented Generation) architecture for richer contextual agricultural reasoning.

---

## UI & User Experience

- Make the interface significantly more reactive and real-time.
- Ensure plans, alerts, and tasks update instantly without manual refreshes.

---

## Notifications & Communication

- Add:
  - SMS notifications
  - email notifications
  - push notifications
- Build job execution audit trails for debugging and operational transparency.

---

## Automation & Background Jobs

- Add:
  - retry logic
  - fallback mechanisms
  - job-failure recovery
- Automatically register crops after sowing completion.
- Add frontend crop management workflows.
- Automatically refresh weather datasets periodically whenever internet connectivity is available.

---

## Chatbot & Intent Classification

- Improve multi-intent understanding.
- Improve conversational context retention across messages.
- Enhance context extraction for agricultural conversations.

---

## Disaster Management

- Add disaster-management workflows tied to crop growth stages.
- Allow farmers to report abnormal crop development.
- Build AI-assisted diagnosis workflows that analyse:
  - historical tasks
  - crop stages
  - environmental conditions
  - operational history

to identify potential causes and recommend corrective actions.
