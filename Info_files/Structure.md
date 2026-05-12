## High Level Architecture Diagram

                ┌──────────────────────────────┐
                │         Farmer App           │
                │ Dashboard | Chat | Alerts    │
                └──────────────┬───────────────┘
                               │
                         HTTP / API
                               │
                ┌──────────────▼───────────────┐
                │     Coordinator Agent        │
                │  (workflow orchestration)    │
                └───────┬───────────┬──────────┘
                        │           │
             User-driven│           │Scheduled
                        │           │
        ┌───────────────▼───┐   ┌───▼────────────────┐
        │     Agents         │   │       Jobs         │
        │ Context / Risk /   │   │ Daily / Weekly     │
        │ Planning / Advisory│   │ Forecast Updates   │
        └───────────────┬────┘   └────┬───────────────┘
                        │             │
                        └──────┬──────┘
                               │
                      ┌────────▼─────────┐
                      │     Services     │
                      │ Planning | Tasks │
                      │ Forecast | Alert │
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │   Rule Engine     │
                      │ (agronomic logic) │
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │   Crop Rules      │
                      └────────┬─────────┘
                               │
   ┌───────────────┬────────────┴────────────┬───────────────┐
   │               │                         │               │
┌──▼────────┐ ┌────▼────────┐        ┌───────▼────────┐ ┌────▼────────┐
│ Plans/DB  │ │ Forecast DB │        │ Soil/Health DB │ │ Gemma (LLM) │
└───────────┘ └─────────────┘        └────────────────┘ └─────────────┘

---

## 📁 Project Structure

```bash

app/
│
├── __init__.py 

├── routes/
│   ├── dashboard.py
│   ├── plans.py
│   ├── tasks.py
│   ├── chatbot.py
│   └── forecasts.py
│
├── agents/
│   ├── coordinator_agent.py
│   ├── context_agent.py
│   ├── risk_agent.py
│   ├── planning_agent.py
│   └── advisory_agent.py
│
├── jobs/
│   ├── daily_update_job.py
│   ├── weekly_update_job.py
│   └── forecast_refresh_job.py
│
├── services/
│   ├── seasonal_planner_service.py
│   ├── weekly_planner_service.py
│   ├── task_generation_service.py
│   ├── task_update_service.py
│   ├── forecast_service.py
│   ├── recommendation_service.py
│   ├── advisory_service.py
│   ├── dashboard_service.py
│   ├── chatbot_service.py
│   └── gemma_service.py
│
├── rules/
│   ├── crop_rules.py
│   └── rule_engine.py
│
├── models/
│   ├── seasonal_plan.py
│   ├── weekly_plan.py
│   ├── task.py
│   ├── weather_forecast.py
│   ├── plan_revision.py
│   └── chat_message.py
│
└── repositories/
    ├── plan_repository.py
    ├── task_repository.py
    └── forecast_repository.py

├── templates/          # HTML (if using server-side rendering)
│   ├── base.html
│   ├── dashboard.html
│   ├── fields.html
│   └── crops.html
│
├── static/             # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── images/
│
├── utils/              # Helpers
│   ├── helpers.py
│   ├── constants.py
│   └── validators.py
│
└── extensions.py       # DB, migrate, etc.
│
├── instance/               # Instance-specific configs
│
├── sead_data.py   
├── config.py               # App config
├── run.py                  # Entry point
├── requirements.txt
├── .env
└── README.md
```

---

🔁 3. Sequence Diagram — Daily Update Flow

Scheduler
   ↓
DailyUpdateJob.run()
   ↓
CoordinatorAgent.handle_daily_system_update()
   ↓
ContextAgent.get_context()
   ↓
RiskAgent.get_risk_context()
   ↓
PlanningAgent.evaluate_daily_update()
   ↓
RuleEngine.apply_rules()
   ↓
IF no major change:
    → TaskUpdateService.update_daily_tasks()
    → AdvisoryAgent.build_daily_advisory()
ELSE:
    → PlanRevisionService.create_proposed_revision()
    → AdvisoryAgent.build_plan_change_advisory()
   ↓
Save results → DB
   ↓
Dashboard + Chat use updated state

---

💬 4. Sequence Diagram — Chatbot Flow

User → Chatbot API
   ↓
CoordinatorAgent.handle_chat()
   ↓
ContextAgent.get_context()
RiskAgent.get_risk_context()
   ↓
ChatContextService.build_prompt()
   ↓
Gemma (LLM)
   ↓
Response:
   - explanation
   - recommendation
   - optional plan change
   ↓
IF user confirms:
   → PlanRevisionService.apply_change()
   → TaskUpdateService.regenerate_tasks()
   ↓
Return response to UI

---

🧠 5. Planning Hierarchy Diagram

                Seasonal Plan (Master)
                ─────────────────────
                Sowing | Irrigation | Harvest

                        ↓

                Weekly Plan (Active Week)
                ─────────────────────────
                Phase + Weekly Objectives

                        ↓

                Daily Tasks (Execution)
                ───────────────────────
                Today’s Actions + Priority

  ---

🔥 6. Change Propagation Flow

Weather Forecast Change
        ↓
Rule Engine Evaluation
        ↓
┌─────────────────────────────┐
│ Minor Impact                │
│ → Update Daily Tasks        │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Medium Impact               │
│ → Update Weekly Plan        │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Major Impact                │
│ → Update Seasonal Plan      │
│ → Create Proposed Revision  │
│ → Ask Farmer Approval       │
└─────────────────────────────┘

---

AgriGemma is a climate-adaptive farm planning system that combines:

A deterministic rule engine for agronomic decisions
A three-layer planning hierarchy (seasonal → weekly → daily)
Scheduled forecast-driven updates via background jobs
A multi-agent orchestration layer for workflow management
A Gemma-powered advisory and chatbot system for explanation and interaction

The system continuously adapts plans based on real-time weather, while ensuring that major changes are explained and confirmed by the farmer before execution.


