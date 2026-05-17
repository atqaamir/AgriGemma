# AgriGemma — Compiled Documentation

_A single-document compilation of every reference doc in `Info_files/`._

Each section below is one original markdown file, nested under a numbered section heading. Headings inside each source file have been demoted so they sit cleanly under their section. Original sources are noted at the top of each section.

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [AI Backend Comparison](#2-ai-backend-comparison)
3. [LiteRT / On-Device Setup](#3-litert-on-device-setup)
4. [AI Setup Summary](#4-ai-setup-summary)
5. [AI Integration Summary](#5-ai-integration-summary)
6. [Notification System](#6-notification-system)
7. [Notification Testing](#7-notification-testing)
8. [Component Template](#8-component-template)
9. [Frontend Verification](#9-frontend-verification)

---

## 1. Project Structure

> _High-level layout of the codebase: backend (Flask + SQLAlchemy), AI orchestration, mobile (Flutter + Capacitor), and supporting modules._


### High Level Architecture Diagram

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

### 📁 Project Structure

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

#### Ollama Approach

```
Flask App → HTTP Request → Ollama Server (localhost:11434) → GPU/CPU Inference
```

**Pros:**
- Standalone service - easy to run separately
- Better GPU optimization
- Faster inference (optimized C++ runtime)
- Can share server across multiple apps
- Supports multiple models simultaneously

**Cons:**
- Extra service to manage
- More memory overhead
- Windows installer required

---

### Performance Benchmarks

#### Inference Speed
```
Prompt: "What crops should I plant in spring?"

Ollama (gemma2:2b):      0.8 seconds
Google Cloud API:        2.1 seconds
```

#### Memory Usage (at rest)
```
Ollama Server:           200-400 MB
LiteRT (model loaded):   1.2-1.5 GB
```

#### Startup Time
```
Ollama Server:           10-15 seconds
```

---

### Use Cases

#### **Ollama** for:
- ✅ fastest inference
- ✅ run multiple models simultaneously
- ✅ standalone service architecture

#### **Google Cloud API** for:
- ✅ best quality responses for chatbot
- ✅ advanced features (vision, etc.)
- ✅ reliable cloud infrastructure

---

### How It Works

```
User Query
    ↓
Flask App
    ↓
GemmaProvider (smart fallback)
    ↓
    ├─→ Ollama:Gemma4:e2b Available? → Load local model → Inference ✓
    │
    ├─→ Google API Key set? → Use google-generativeai ✓
    │
    └─→ No AI backend? → Placeholder responses
```


### Fallback Behavior

The provider automatically falls back if:

1. **Gemma4 fails to initialize** → Tries Google API
2. **Google API not available** → Uses placeholder responses
3. **Inference errors** → Returns helpful fallback message

---


### System Overview

#### Core Components

1. **Notification Model** (`app/models/notification.py`)
   - Types: `info`, `warning`, `critical`, `recommendation`

2. **AI Model Service** (Modular & Provider-based)

3. **Task Intelligence Service** (`app/services/task_intelligence_service.py`)

4. **Task Event Service** (`app/services/task_event_service.py`)

5. **Notification UI** (`app/templates/notification_ui.html`)


#### Notification Types & Display

| Type | Symbol | Color | Use Case | Behavior |
|------|--------|-------|----------|----------|
| `info` | ℹ️ | Blue | General information | Dropdown only |
| `warning` | ⚠️ | Orange | Important but non-critical | Dropdown only |
| `critical` | 🚨 | Red | Urgent alerts | Popup + Dropdown |
| `recommendation` | 💡 | Green | AI-driven suggestions | Dropdown (clickable for details) |


### ✅ Expected Behavior

#### Bell Icon States
| State | Appearance |
|-------|-----------|
| No notifications | Grey 🔔 |
| Has unread | Red 🔔 with count |
| Hovered | Darker color |
