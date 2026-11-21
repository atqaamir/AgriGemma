# AgriGemma: A Climate-Smart Seasonal Planner for Smallholder Farmers

A farming assistant that keeps a season plan, checks the weather forecast every day, moves tasks when the
weather changes, and uses Gemma 4 to explain the plan and answer the farmer's questions.

**Live demo:** https://agrigemma.onrender.com (free instance: the first request after a quiet period can take a
minute while it wakes up)

> **Status: frozen (November 2026).** This repository is the public, stable version of AgriGemma and the code behind
> the live demo. It is no longer under active development; new work continues in a separate repository.
> Scope decisions, known limitations and planned work are in [ASSUMPTIONS.md](ASSUMPTIONS.md).

---

## The Problem

Climate change has made traditional farming calendars unreliable, and smallholder farmers are hit hardest:

- Rainfall is unpredictable and no longer follows seasonal patterns.
- Heatwaves and droughts arrive without warning.
- Planting windows are shifting, so last year's schedule can be wrong for this year.
- Yields drop when plans cannot adapt, and the economic risk falls entirely on the farmer.

The result: farmers sow at the wrong time, irrigate inefficiently and lose harvests to conditions they could not
anticipate.

---

## The Solution

AgriGemma turns forecasts into concrete farming decisions: what to do, when, and why.

1. **Season plan.** Each field has a crop with planned dates for sowing, irrigation start, fertilization and harvest.
2. **Rolling weekly plan.** Every morning the next 7 days are rebuilt from the season plan and checked against the
   forecast with agronomic rules. If the weather is unsuitable, an event moves to the first suitable day.
3. **Daily tasks.** The weekly plan becomes the farmer's to-do list ("Sow Maize – North Field"). Tasks move with
   the plan instead of being discarded.
4. **Explanations and chat.** Gemma 4 explains why each task matters, writes the change notifications and a farm
   report, and answers questions in a chatbot that knows the farm.

**Design rule: the rules decide, the AI explains.** When to sow is decided by a deterministic, auditable rule base.
A wrong guess there costs the farmer a crop, so the model never decides it. Gemma 4 is used where language matters:
explanations, summaries, recommendations the farmer can accept or reject, and conversation.

---

## Try the Demo

Open the live demo and go to **My Tasks**. The demo date is fixed at 5 May 2027 (Kharif sowing season in Punjab), so
the demo always shows the same starting point.

The **Weather Change Simulator** applies a forecast change and runs the full daily update immediately, instead of
waiting for the 5:00 AM job. The info icon next to each scenario explains the change and the expected result.

| Scenario | What changes | What the rules do |
|---|---|---|
| Light showers (normal for May) | 8 mm and 4 mm of rain, cloud and 27–28 °C on 7–8 May | Cotton sowing moves from 7 to 9 May; maize stays on 6 May |
| Heavy rain (unusual for May) | 38, 62 and 45 mm of rain on 6–8 May | Seed beds are waterlogged: maize and cotton sowing move to 10 May |
| Sowing window running out | Cotton was planned for 24 April and not sown; cloudy 5–8 May | No suitable day left in the 14-day sowing window: a "Decide: Cotton sowing" task with an AI recommendation. The farmer chooses **Sow anyway** or **Skip** (both can be undone) |

After a scenario, look at the task list, the weekly plan, the notifications and the dashboard, and ask the chatbot
about it (for example "Why did my maize sowing move?"). **Reset demo** puts the farm back to the starting state.

The demo has one shared farm and no login, so other visitors' clicks are visible too. The simulator can run once per
30 seconds per user and Reset once per 60 seconds; admin tools are switched off on the live demo.

---

## How It Works

### Architecture

A layered Flask application. Requests always flow top to bottom:

```
Routes (pages and APIs: /mytasks, /myfields, /mycrops, /chatbot, /notifications, /weather)
  → Agents      (orchestration: CoordinatorAgent and the agents it calls)
  → Services    (rules, planning, tasks, risk, AI, chatbot)
  → Repositories (database access)
  → Models      (SQLAlchemy: PostgreSQL on Render, SQLite locally)
```

The agents are plain Python classes that coordinate the work, not LLM agents. Routes never call agents directly:
everything goes through the `CoordinatorAgent`, which calls the `RiskAgent`, `PlanningAgent`, `NotificationAgent`
and `DashboardAgent`.

### The daily update (5:00 AM)

`CoordinatorAgent.daily_update` runs the same pipeline for every farm:

1. **Roll the weekly plan** forward to today..today+6 from the season plan.
2. **Assess the weather change** against yesterday's forecast (`RiskService`): no change, change without impact,
   impact on the plan, or impact on today's tasks.
3. **Apply the forecast to the plan** with the rule engine: events on unsuitable days move; sowing uses a window
   (below).
4. **Sync the tasks** with the plan: move, cancel or reactivate plan tasks across the 7 days, and create today's and
   tomorrow's tasks (no duplicates).
5. **Notify and refresh:** change notifications (AI-written, with a rule-based fallback) and the dashboard. The
   impact level sets how urgent the notification is.

Running it twice gives the same result: the real dates of events (moved by the forecast, completed or planned by the
farmer) are stored as an append-only change log (`plan_event_override`) with the day each decision was made, and the
day's forecast decisions are recalculated rather than applied again.

### Rule engine and the sowing window

The rule base (`Data_Setup/`) maps crop × growth stage × weather or soil factor to a suitability score and a
feasibility band (Ideal / Conditional / Not Feasible), with reasons and recommended actions. Lookup tables cover
ranges, thresholds, compatibility, actions and crop calendars.

Sowing is treated as a window, not a fixed date: from the planned date to 14 days later. Each day the rules check the
forecast; the first suitable day wins, and sowing can also move earlier again when the weather improves. Heavy rain
(20 mm or more) marks the seed bed as waterlogged for that day and the next. If no suitable day is left, the farmer
gets a **decision-needed** task with the facts and an AI recommendation; the farmer decides. Irrigation is recurring
and recalculated daily; fertilization and harvest still move by a fixed delay (see Future Work).

### AI layer

- **Provider interface** (`AIModelProvider`): Google AI Studio (`gemma-4-26b-a4b-it`), Ollama (offline), LiteRT
  (on-device) and a placeholder provider for tests. Chat uses streaming; background texts use short, low-latency calls.
- **Resilience:** on 503, 429 or a timeout the Google provider retries with a fallback model
  (`GOOGLE_AI_FALLBACK_MODEL`). Every AI feature has a rule-based fallback, so the app works without a model.
- **Chatbot:** keyword intent detection with an AI fallback for unclear questions, a per-user context built from the
  farm's data (plan, tasks, weather compared with normal for the month), web search only for non-farming questions,
  and the last 6 messages for follow-ups.
- **Task insights and farm report:** the code collects signals from the farm data; one AI call turns them into a
  short report that must cite those signals, and the "Based on" lines are built by code, not by the model. Reports are
  stored and marked as outdated when the farm changes.
- **"Why" explanations** for plan tasks and **recommendations** for decision-needed tasks.
- **Output guard:** every user-facing AI text is checked for leaked drafts, unknown crops and a tone that doesn't
  match the forecast; failing texts are replaced by the rule-based version.

### Scheduled jobs

| Job | Schedule (UTC) | Purpose |
|---|---|---|
| Daily update | 05:00 | Weekly plan, weather check, plan and task updates, notifications |
| Task generator | 19:00 | Tomorrow's tasks from the weekly plan |
| Weekly plan | Monday 03:30 | Rebuilds the weekly plan (now redundant: the daily update rolls it every day) |

The app runs with one gunicorn worker (4 threads), so the in-process scheduler runs once.

### Quality

- Unit and integration tests with the placeholder AI provider (`Test_Runs/`).
- Evals with the real model: 40+ chatbot questions (including Roman Urdu), task insights, farm report and "Why"
  explanations, checked against the farm's data.
- Runtime guards on every AI output (above).

---

## Features

- **Dashboard:** today's weather, alerts, task insights and the AI farm report.
- **My Tasks:** today's tasks with priority, "Why" explanations and a "Recommended order" view.
- **Weekly plan:** the next 7 days per crop, with moved events and decisions explained.
- **Notifications:** info, warning, critical and recommendation; critical ones pop up.
- **Chatbot:** questions about the farm in natural language, answered from the farm's data.
- **Fields and crops:** land, fields, active crops, soil conditions.
- **Mobile-first UI** (Capacitor wrapper in `android/` and `mobile/`).

---

## Installation & Setup

See [SETUP.md](SETUP.md). Quick start:

```bash
# Windows
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python run.py
# Mac/Linux
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python run.py
```

Main environment variables: `DATABASE_URL`, `USE_GOOGLE_AI`, `GOOGLE_API_KEY`, `GOOGLE_AI_MODEL`,
`GOOGLE_AI_FALLBACK_MODEL`, `DEMO_TODAY` (fixed demo date), `DEMO_ADMIN_ENABLED` (admin tools, off on the live demo),
`SECRET_KEY`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (Python), SQLAlchemy |
| Frontend | JavaScript, Jinja2 templates (mobile-first), Capacitor |
| Database | PostgreSQL (Render) / SQLite (local) |
| AI (cloud) | Gemma 4 (`gemma-4-26b-a4b-it`) via Google AI Studio, with a fallback model |
| AI (offline) | Gemma 4 via Ollama, or on-device via LiteRT |
| Weather | Simulated from monthly climate profiles for the demo (an OpenWeatherMap client is included) |
| Background jobs | APScheduler |
| Hosting | Render (gunicorn), GitHub Actions keep-alive ping on `/health` |

---

## Known Limitations

- **Demo data:** the season plan is seeded (a fixed list of crops, fields and planned dates for the demo farm), and
  every restart or Reset reseeds the demo. There is no login.
- **Weather is simulated** from monthly climate profiles for three Pakistani regions, not a live API.
- **Growth stages do not advance** over time yet; the demo crops are in the sowing stage.
- **Rule thresholds are placeholders** until an agronomist validates them (for example the 14-day sowing window and
  the 20 mm waterlogging threshold). Kharif crops only (rice, maize, cotton); no Rabi crops such as wheat.
- **Only sowing uses a window;** fertilization and harvest move by a fixed delay.
- Tasks are scheduled by date, not time of day; no labour, water or equipment limits.
- The scheduler runs inside the web process, and the steps of the daily update commit separately.

Full list and planned work: [ASSUMPTIONS.md](ASSUMPTIONS.md) (Assumptions, Known Limitations, Future Work).

---

## Target Users

Small and medium-scale farmers in Pakistan, often with limited literacy and technical experience, mostly on mobile
phones. Design principles: simple, visual (icons, colour coding, little text), action-driven (every insight leads to
a task), and explainable.

---

## Hackathon Context

AgriGemma was first built for the **Gemma 4 Good Hackathon (Kaggle)** and then reworked afterwards (rolling weekly
plan, real event dates, sowing window and decisions, grounded AI texts, evals and the live demo). Gemma 4 is used as a
decision explainer and assistant, not as a weather predictor or the decision-maker.

---

## Authors

**Atqa R. Amir** — Full Stack AI Engineer
**Amna Bukhari** — Full Stack AI Engineer
**Azka Abiya Amir** — Visual Content Creator

---

## License

Non-commercial use only. See [LICENSE](LICENSE).
