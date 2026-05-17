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

<sub>Source: `Info_files/Structure.md`</sub>

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

---

## 2. AI Backend Comparison

> _Trade-offs evaluated when choosing the local AI execution stack (Ollama, LiteRT, MediaPipe, etc.)._

<sub>Source: `Info_files/AI_BACKEND_COMPARISON.md`</sub>

### Overview

SmartFarming now supports **two local AI backends** for running Gemma:

| Feature | Ollama | LiteRT (Google AI Edge) |
|---------|--------|------------------------|
| **Installation** | Standalone installer | pip packages |
| **Setup Time** | ~5 minutes | ~2 minutes |
| **Model Download** | ~3.5GB | ~3.5GB |
| **Internet Required** | After setup | Only for setup |
| **Dependencies** | None (standalone) | mediapipe, numpy |
| **Speed** | 0.3-1s per response | 0.5-2s per response |
| **GPU Support** | Yes (easy) | Yes (needs config) |
| **RAM Usage** | Consistent | Varies with model |
| **Quality** | Good | Good |

---

### Architecture Comparison

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

#### LiteRT Approach

```
Flask App → Python TensorFlow Lite Runtime → Direct GPU/CPU Inference
```

**Pros:**
- Single Python process
- No extra service
- Simpler deployment
- Direct integration with app
- Smaller memory footprint

**Cons:**
- Model loads per request (first time slower)
- Python-only (less optimized than C++)
- One model at a time

---

### Setup Comparison

#### Ollama Setup (5 minutes)
```bash
1. Download installer from https://ollama.ai
2. Install and restart computer
3. Run: ollama pull gemma2:2b
4. Run: ollama serve
5. Start app: flask run
```

#### LiteRT Setup (2 minutes)
```bash
1. pip install mediapipe numpy
2. Start app: flask run
   (Model auto-downloads on first chat)
```

---

### Performance Benchmarks

#### Inference Speed
```
Prompt: "What crops should I plant in spring?"

Ollama (gemma2:2b):      0.8 seconds
LiteRT (gemma2:2b):      1.2 seconds
Google Cloud API:        2.1 seconds
```

#### Memory Usage (at rest)
```
Ollama Server:           200-400 MB
LiteRT (not loaded):     50 MB
LiteRT (model loaded):   1.2-1.5 GB
```

#### Startup Time
```
Ollama Server:           10-15 seconds
Flask App (LiteRT):      2-3 seconds
```

---

### Use Case Recommendations

#### Choose **Ollama** if:
- ✅ Want fastest inference
- ✅ Running multiple apps that need AI
- ✅ Have dedicated GPU with CUDA
- ✅ Want to run multiple models simultaneously
- ✅ Prefer standalone service architecture

#### Choose **LiteRT** if:
- ✅ Want minimal setup/dependencies
- ✅ Running single Flask app
- ✅ Prefer Python-only solution
- ✅ Have limited disk space for services
- ✅ Want simpler Docker deployment

#### Choose **Google Cloud API** if:
- ✅ Want best quality responses
- ✅ Need advanced features (vision, etc.)
- ✅ Don't mind monthly costs (~$0.50-2 per million tokens)
- ✅ Want reliable cloud infrastructure

---

### Fallback Chain

SmartFarming's AI provider tries backends in this order:

```
1. LiteRT (local, fastest if available)
   ↓
2. Google Cloud API (if GEMMA_API_KEY set)
   ↓
3. Placeholder responses (rules-based fallback)
```

This means:
- **If LiteRT fails** → automatically tries API
- **If API unavailable** → still provides helpful responses
- **User always gets an answer**

---

### Migration Guide

#### From Ollama to LiteRT

**Step 1:** Install LiteRT
```bash
pip install mediapipe numpy google-generativeai
```

**Step 2:** Stop Ollama
```bash
# Windows: Close ollama.exe
# Or: net stop ollama (if installed as service)
```

**Step 3:** Start Flask
```bash
flask run
# Model will auto-download on first chat
```

#### From LiteRT to Ollama

**Step 1:** Install Ollama from https://ollama.ai

**Step 2:** Pull model
```bash
ollama pull gemma2:2b
```

**Step 3:** Start Ollama server
```bash
ollama serve
```

**Step 4:** Start Flask
```bash
flask run
```

No code changes needed - provider auto-detects backend!

---

### Troubleshooting

#### "No AI backend available"
**Solution:**
```bash
# Install LiteRT deps
pip install mediapipe numpy

# Or set API key
set GEMMA_API_KEY=your-key

# Or install Ollama from https://ollama.ai
```

#### "Slow first request"
**Cause:** LiteRT is loading model into memory
**Solution:** First request takes 10-30s, subsequent are fast

#### "Model too large for memory"
**Solution:**
- Reduce to 2B model: `GEMMA_MODEL_PATH=gemma-2-2b-it-gpu-int8.tflite`
- Or use API with smaller quota

#### "Inference very slow"
**Solution:**
- Using CPU inference (enable GPU)
- Using large model (switch to 2B)
- Check system resources with Task Manager

---

### Environment Variables

#### LiteRT Configuration
```bash
# Disable LiteRT, use only API
USE_LITERT_MODEL=false

# Custom model path
GEMMA_MODEL_PATH=C:\path\to\model.tflite

# Model directory
GEMMA_MODEL_DIR=C:\models
```

#### API Configuration
```bash
# Google Cloud API key
GEMMA_API_KEY=sk-...

# Alternative Google AI library
USE_PLACEHOLDER_AI=true
```

#### General
```bash
# Force placeholder (no AI)
USE_PLACEHOLDER_AI=true

# Ollama endpoint (if using Ollama)
GEMMA_API_URL=http://localhost:11434/api/generate
```

---

### Cost Comparison

#### Ollama (Local)
- **Initial:** ~2GB disk for model
- **Per query:** $0
- **Monthly:** $0

#### LiteRT (Local)
- **Initial:** ~3.5GB disk for model
- **Per query:** $0
- **Monthly:** $0

#### Google Cloud API
- **Initial:** Free tier (60 RPM limit)
- **Per query:** $0.075 per 1M input tokens
- **Monthly:** ~$0.50-2.00 (farm advisor usage)

---

### Deployment Considerations

#### Docker Deployment

**With LiteRT:**
```dockerfile
FROM python:3.11
RUN pip install -r requirements.txt
COPY . .
CMD ["flask", "run"]
# Total image: ~1.5GB
```

**With Ollama:**
```dockerfile
FROM ollama/ollama:latest
# Separate Ollama container + Flask container
# More complex setup, better performance
```

---

### Monitoring

#### Check Which Backend is Active

```python
from app.services.ai_model_service import ai_model_service

provider = ai_model_service.get_provider()
print(f"Active: {provider.name}")
# Output: "Gemma 2 (LiteRT - Local Edge)" or similar
```

#### View Logs
```bash
# Flask logs show provider initialization
flask run --debug
# Look for: "✅ LiteRT Gemma model loaded" or similar
```

---

### Recommendation

**For SmartFarming:**

1. **Development/Testing:** Use **LiteRT**
   - Quick setup, no extra services
   - Self-contained in Flask app
   
2. **Production with GPU:** Use **Ollama**
   - Better performance
   - Can scale to multiple workers
   
3. **Production without GPU:** Use **LiteRT + Cloud fallback**
   - Auto-downloads model
   - Falls back to cloud if needed
   - Balances cost and performance

---

### Next Steps

#### Current Status
- ✅ `gemma_provider.py` updated to use LiteRT
- ✅ `requirements.txt` updated with dependencies
- ✅ Smart fallback configured

#### To Use LiteRT
```bash
pip install mediapipe numpy
flask run
```

#### To Use Ollama (instead)
```bash
# Just start Ollama
ollama serve
# Then in another terminal
flask run
# Provider will auto-detect and use Ollama
```

#### To Use Cloud API
```bash
set GEMMA_API_KEY=your-key
flask run
```

All three work seamlessly - the provider auto-selects the best available! 🚀

---

## 3. LiteRT / On-Device Setup

> _Configuration notes for running Gemma on-device via LiteRT._

<sub>Source: `Info_files/LITERT_SETUP.md`</sub>

### Overview

SmartFarming now supports **Google AI Edge / LiteRT** for running Gemma 2 locally without Ollama.

**Key Benefits:**
- ✅ No Ollama installation needed
- ✅ Fully local inference on CPU/GPU
- ✅ Quantized model (~3.5GB)
- ✅ Auto-downloads model on first run
- ✅ Falls back to Google API if available
- ✅ Fallback to placeholder if no backend available

---

### Quick Start

#### Step 1: Install Dependencies

```bash
# Required for LiteRT (fully local)
pip install mediapipe numpy

# Optional: for cloud fallback
pip install google-generativeai
```

#### Step 2: Start SmartFarming

```bash
flask run
```

**That's it!** The app will:
1. Try to use LiteRT local model (auto-downloads on first run)
2. Fall back to Google API if `GEMMA_API_KEY` is set
3. Use placeholder responses if neither is available

#### Step 3: First Run

The first time you use the chatbot:
- Model downloads (~3.5GB to `~/.gemma_models/`)
- Takes 10-30 minutes depending on internet
- Subsequent runs are instant

---

### Configuration Options

#### Option A: Local LiteRT (Default - No Internet After Setup)
```bash
# Just install and run
pip install mediapipe numpy
flask run
```

#### Option B: Google Cloud API Fallback
```bash
# Set API key for fallback
set GEMMA_API_KEY=your-api-key-here
flask run
```

Get API key: https://ai.google.dev/

#### Option C: Custom Model Path
```bash
# Use custom model location
set GEMMA_MODEL_PATH=C:\path\to\gemma-2-2b-it-gpu-int8.tflite
flask run
```

#### Option D: Force API Only (No Model Download)
```bash
# Skip LiteRT, use API only
set USE_LITERT_MODEL=false
set GEMMA_API_KEY=your-api-key
flask run
```

---

### Model Information

#### Gemma 2 2B (Quantized - Int8)

| Property | Value |
|----------|-------|
| Size | 3.5 GB |
| RAM Required | 4 GB minimum |
| Speed | Fast (~0.5-2 sec per response) |
| Quality | Good for farming advice |
| Quantization | INT8 (reduced precision) |
| Download | Auto-downloads on first use |

#### Available Models

Other Gemma models (download manually if desired):
- `gemma-2-9b-it-gpu-int8.tflite` - 9B model, better quality, needs 8GB+ RAM
- `gemma-2-2b-it-cpu.tflite` - CPU-optimized version

---

### Troubleshooting

#### "ModuleNotFoundError: No module named 'mediapipe'"
**Solution:**
```bash
pip install mediapipe numpy
```

#### "Model download failed"
**Solution:**
1. Check internet connection
2. Manual download from: https://github.com/google-generativeai/llm-inference-benchmarks/releases
3. Set `GEMMA_MODEL_PATH` to manual path

#### "LiteRT model not available"
**Solution:**
```bash
# Ensure mediapipe is installed
pip install --upgrade mediapipe

# Try downloading model again
python -c "from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider; GemmaProvider()"
```

#### Slow responses
**Causes & Solutions:**
- CPU inference - get GPU support: https://tensorflow.org/lite/guide/gpu
- Model too large - use 2B instead of 9B
- First request always slower (model initialization)

#### Model path permission denied
**Solution:**
```bash
# Use custom location with write permission
set GEMMA_MODEL_PATH=C:\Users\YourUser\gemma_models\model.tflite
```

---

### Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| RAM | 4 GB minimum, 8 GB recommended |
| Disk | 10 GB free (for model + cache) |
| CPU | Modern multi-core (ARM/x86) |
| GPU | Optional - for faster inference |

#### GPU Support

For GPU acceleration, install TensorFlow GPU:
```bash
pip install tensorflow-gpu  # For NVIDIA CUDA
# or
pip install tensorflow-metal  # For Apple Metal
```

---

### How It Works

```
User Query
    ↓
Flask App
    ↓
GemmaProvider (smart fallback)
    ↓
    ├─→ LiteRT Available? → Load local model → Inference ✓
    │
    ├─→ Google API Key set? → Use google-generativeai ✓
    │
    └─→ No AI backend? → Placeholder responses
```

---

### Performance Comparison

| Backend | Latency | Quality | No Internet | Cost |
|---------|---------|---------|-------------|------|
| **LiteRT** | 0.5-2s | Good | ✅ Yes | Free |
| Google API | 1-3s | Excellent | ❌ No | $$ |
| Ollama | 0.3-1s | Good | ✅ Yes | Free |

---

### Fallback Behavior

The provider automatically falls back if:

1. **LiteRT fails to initialize** → Tries Google API
2. **Google API not available** → Uses placeholder responses
3. **Inference errors** → Returns helpful fallback message

Example response chain:
```
LiteRT model error 
  → Try Google API
  → No API key available
  → Use placeholder response
  → User still gets helpful advice
```

---

### Development Tips

#### Test Model Locally
```python
from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider

provider = GemmaProvider()
print(f"Provider: {provider.name}")
response = provider.complete("What is soil pH?")
print(response)
```

#### Monitor First Run
```bash
# Watch model download progress
flask run --debug
# Check ~/.gemma_models/ directory during download
```

#### Use Placeholder for Testing
```bash
# Test app without downloading model
set USE_PLACEHOLDER_AI=true
flask run
```

---

### Cleanup

#### Remove Cached Model
```bash
# Windows
rmdir /s %USERPROFILE%\.gemma_models

# Unix/Mac
rm -rf ~/.gemma_models
```

Model will re-download on next run if needed.

---

### Next Steps

1. **Install:** `pip install mediapipe numpy`
2. **Run:** `flask run`
3. **Use:** Click "Chat" → Start chatting with local Gemma!

---

### Additional Resources

- MediaPipe Text Generator: https://developers.google.com/mediapipe/solutions/text/text_generator
- Gemma Models: https://www.kaggle.com/models/google/gemma
- TFLite Optimization: https://www.tensorflow.org/lite/guide/optimize

---

## 4. AI Setup Summary

> _End-to-end summary of how AgriGemma's AI stack is provisioned and wired in._

<sub>Source: `Info_files/AI_SETUP_SUMMARY.md`</sub>

### Recent Updates ✅

#### 1. Dashboard Page
- ✅ Full dashboard created at `/dashboard`
- Displays farm overview (totals, acreage, crops)
- Shows critical tasks with priority indicators
- Real-time soil condition metrics (moisture, heat, stress)
- Field & crop health status breakdowns
- Critical alert banner for urgent issues
- Auto-refreshes every 30 seconds

#### 2. Chat Navigation
- ✅ Fixed chat links in all pages:
  - `fields.html` → `/chatbot`
  - `tasks.html` → `/chatbot`
  - `crops.html` → `/chatbot`
  - `chatbot.html` → `/chatbot` (active nav)
  - `dashboard.html` → `/chatbot` (quick action)

#### 3. Notifications
- ✅ "View all notifications" button linked to `/notifications`
- Routes already configured for:
  - GET `/notifications/` - All notifications (paginated)
  - GET `/notifications/unread` - Unread only
  - GET `/notifications/unread/count` - Count only
  - GET `/notifications/unread/critical` - Critical alerts
  - PUT `/notifications/{id}/read` - Mark as read
  - PUT `/notifications/read-all` - Mark all as read

---

### Ollama + Gemma Setup

#### Current Status
- ✅ `gemma_provider.py` configured for Ollama at `localhost:11434`
- ✅ HTTP-based integration (no additional packages needed)
- ⏳ **Pending:** Install Ollama & pull Gemma 2 model

#### Quick Start (Windows)

##### Step 1: Install Ollama
1. Download from https://ollama.ai
2. Run Windows installer
3. Restart computer
4. Verify: Open Command Prompt and run `ollama --version`

##### Step 2: Pull Gemma 2 Model
```bash
ollama pull gemma2:2b
```
This downloads ~3.5GB (first time only, takes 5-10 minutes)

##### Step 3: Start Ollama Server
Double-click `start_ollama.bat` in the project root
- Or run: `ollama serve`
- Server runs on http://localhost:11434

##### Step 4: Start SmartFarming
```bash
flask run
```

##### Step 5: Test
1. Navigate to http://localhost:5000
2. Click "Chat" button in footer
3. Send a message like "What crops should I plant?"
4. Chatbot responds with Gemma 2-generated text

---

### Files Created/Updated

#### New Files
- `/dashboard.html` - Full farm dashboard with metrics & alerts
- `OLLAMA_SETUP.md` - Comprehensive Ollama setup guide
- `start_ollama.bat` - Windows quick-start script for Ollama
- `start_ollama.sh` - Unix quick-start script for Ollama

#### Updated Files
- `fields.html` - Chat link fixed
- `tasks.html` - Chat link fixed
- `crops.html` - Chat link fixed

---

### Model Options

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| **gemma2:2b** | 3.5GB | 4GB | Fast ✓ | Good |
| gemma2:7b | 15GB | 8GB+ | Moderate | Excellent |
| gemma2:7b-q4 | 9GB | 6GB | Moderate | Good |

**Recommendation:** Use `gemma2:2b` for development (faster, less VRAM)

---

### Environment Variables

#### Use Gemma (Default)
No setup needed - app uses `localhost:11434` by default

#### Use Placeholder AI (For Testing Without Ollama)
```bash
set USE_PLACEHOLDER_AI=true
flask run
```

#### Custom Ollama Endpoint
```bash
set GEMMA_API_URL=http://your-server:11434/api/generate
flask run
```

---

### Troubleshooting

#### "Connection refused on port 11434"
- Ollama is not running
- Run `ollama serve` in Command Prompt
- Wait 3-5 seconds for server to initialize

#### "Model not found"
- Model not downloaded
- Run `ollama pull gemma2:2b`
- Wait for download to complete

#### Slow responses
- You're using 7B model on limited hardware
- Try 2B model instead: `ollama pull gemma2:2b`
- Or reduce model size

#### "AI model failed: HTTPConnectionPool..."
- Ollama server crashed or stopped
- Restart it: `ollama serve`
- Check if port 11434 is blocked

---

### Next Steps

1. **Install Ollama** from https://ollama.ai
2. **Run setup script**: Double-click `start_ollama.bat`
3. **In new terminal**: Run `flask run`
4. **Test chatbot**: Visit http://localhost:5000 → Chat

For detailed setup instructions, see `OLLAMA_SETUP.md`

---

### Current AI Integration

- ✅ Chatbot Service - Context-aware farming advice
- ✅ Task Intelligence - AI-powered task recommendations
- ✅ Farming Knowledge Base - 100+ rules for crops/diseases/pests
- ✅ Dashboard Service - Farm overview & metrics
- ⏳ **Pending Ollama installation** to enable AI responses

Once Ollama is set up, all AI features will be fully functional!

---

## 5. AI Integration Summary

> _How agents, services, and the AI execution layer are integrated across the system._

<sub>Source: `Info_files/AI_INTEGRATION_SUMMARY.md`</sub>

### Summary
Removed caching from task intelligence generation and fully integrated Gemma AI into the task generation, task intelligence, and notification pipelines. All AI recommendations are now persisted to the database at generation time, with fresh Gemma calls on every dashboard/task page load.

---

### Changes Made

#### 1. **TaskIntelligenceService** (`app/services/intelligence_service/task_intelligence_service.py`)
**Before:** Cached full task intelligence response (300s TTL) per user.  
**After:** No caching. Fresh Gemma calls on every request.

**New Methods:**
- `generate_task_overview(context, user_id)` → Returns one-liner summary of critical tasks for Tasks page header
- `generate_task_explanation(task, context)` → Explains why a specific task was generated; result stored in `Task.ai_explanation` at creation time
- `invalidate_cache()` → No-op for backward compatibility

**Fallback Behavior:**
- Rule-based intelligence if Gemma unavailable, never blank
- `_build_task_overview_fallback()` for task overview summary
- `_build_rule_based_fallback()` for full intelligence JSON

---

#### 2. **TaskGenerationService** (`app/services/task_generation_service.py`)
**Before:** Placeholder that returned text strings like "Irrigation needed".  
**After:** AI-driven task generation that creates persistent Task records with explanations.

**New Logic:**
1. Collect active fields, weekly plan, seasonal plan, existing tasks
2. For each condition (low moisture, poor health, growth stage review, weekly tasks):
   - Check if task title already exists (dedup)
   - Create Task record with title, priority, description
   - **Call `TaskIntelligenceService.generate_task_explanation()` to get AI reasoning**
   - Persist explanation to `Task.ai_explanation` in database
3. Return dict: `{created: N, task_ids: [...], seasonal_plan, weekly_plan}`

**Replaces manual rule-based task generation.**

---

#### 3. **DashboardService** (`app/services/dashboard_service.py`)
**Before:** Placeholder `_build_ai_insights()` that returned hardcoded string.  
**After:** Calls `TaskIntelligenceService.generate_intelligence()` to get fresh Gemma-generated dashboard summary.

**Updated Dashboard Data:**
- `dashboard_summary` — AI-generated 2-3 sentence farm overview
- `dashboard_recommendations` — List of AI-generated actionable recommendations
- `insights` — Array of AI observations from the full intelligence JSON

**All via fresh Gemma call on every dashboard load.**

---

#### 4. **NotificationService** (`app/services/domain_service/notification_service.py`)
**Before:** `generate_alerts()` detected alerts but only logged explanations; didn't persist them.  
**After:** Creates Notification records with AI-generated `detail` field on every call.

**New Logic:**
- `generate_alerts(user_id, tag)` → Detects alerts + generates batch AI explanation → Creates Notification records with detail
- `generate_notifications(user_id, tag)` → Wrapper for backward compat with NotificationAgent
- `generate_alert_for_user(user_id, context)` → Direct consumer interface; returns created notification IDs

**First alert in batch gets full explanation; others get individual alert message.**

---

#### 5. **IntelligenceAgent** (`app/agents/intelligence_agent.py`)
**Before:** `generate(user_id)` → always called `generate_intelligence()`  
**After:** Supports tag parameter to dispatch to different intelligence methods.

**Routes:**
- `tag=None` or `tag="full"` → `TaskIntelligenceService.generate_intelligence()` (full farm overview)
- `tag="critical_task_overview"` → `TaskIntelligenceService.generate_task_overview()` (Tasks page header)

---

#### 6. **CoordinatorAgent** (`app/agents/coordinator_agent.py`)
**Before:** `generate_task_intelligence()` was commented out.  
**After:** Uncommented and active; orchestrates task intelligence generation.

**Coordinator Workflows:**
- `daily_update()` calls `call_intelligence(user_id, tag="critical_task_overview")` after task generation
- Always refreshes dashboard at end (`dashboard_refresh()`)
- Fallback JSON returned on any exception

---

#### 7. **PlanningAgent** (`app/agents/planning_agent.py`)
**Before:** Methods had incompatible signatures (field_id, context).  
**After:** Updated to match coordinator signatures.

**Methods:**
- `generate_daily_tasks(user_id, tag="")` → Status.SUCCESS/FAILED
- `generate_seasonal_plan(user_id, tag="")` → Status.SUCCESS/FAILED

---

#### 8. **ContextAggregationService** (`app/services/intelligence_service/chatbot_service/context_aggregation_service.py`)
**Added Collectors:**
- `_collect_seasonal_plan(user_id)` → SeasonalPlannerService
- `_collect_weekly_plan(user_id)` → WeeklyPlannerService

**Context now includes:** seasonal_plan, weekly_plan

---

#### 9. **Task Route** (`app/routes/_page_tasks.py`)
**Removed:** TaskEventService.on_task_change() calls (no longer needed; AI explanations persisted at creation time)

**Route:** `GET /intelligence` → Calls `coordinator.generate_task_intelligence(user_id)` → Returns TaskIntelligenceSchema

---

#### 10. **Task Model** (`app/models/task.py`)
**Unchanged**, but now utilized:
- `ai_explanation` field persisted when task created by `TaskGenerationService`

---

### Data Flow

#### Task Generation Pipeline
```
CoordinatorAgent.task_generation(user_id)
  → PlanningAgent.generate_daily_tasks(user_id)
    → TaskGenerationService.generate_daily_tasks(user_id)
      1. Collect fields, plans, context
      2. For each condition, create Task record
      3. Call TaskIntelligenceService.generate_task_explanation(task, context)
      4. Persist Task.ai_explanation to DB
      → Return {created: N, task_ids: [...]}
  → DashboardAgent.refresh_dashboard(user_id)
  → call_intelligence(user_id, tag="critical_task_overview")
    → TaskIntelligenceAgent.generate(user_id, tag="critical_task_overview")
      → TaskIntelligenceService.generate_task_overview(context, user_id)
        → Calls Gemma with build_critical_tasks_overview_prompt
        → Returns one-liner for Tasks page header
```

#### Dashboard Pipeline
```
GET /dashboard/<user_id>
  → DashboardService.build_dashboard_data(user_id)
    1. Collect fields, tasks, crops, weather, etc.
    2. Build context via ContextAggregationService
    3. Call TaskIntelligenceService.generate_intelligence(context, user_id)
       → Calls Gemma with build_dashboard_summary_prompt
       → Returns {summary, priority_level, recommendations, urgent_actions, risks, insights}
    4. Include in dashboard_data:
       - dashboard_summary
       - dashboard_recommendations
       - insights
    → Return full dashboard JSON
```

#### Notification Pipeline
```
CoordinatorAgent.send_notification(user_id, tag=tag)
  → NotificationAgent.generate_notifications(user_id, tag=tag)
    → NotificationService.generate_notifications(user_id, tag=tag)
      1. Call _detect_from_context(context)
      2. Call _generate_ai_explanation(alerts, context) [fresh Gemma]
      3. For each alert, create Notification record with:
         - title/message = alert.message
         - detail = AI explanation (first alert) or individual alert (rest)
         - notification_type = CRITICAL or WARNING
      → Return Status.SUCCESS
```

---

### Fallback Behavior

**All three pipelines have rule-based fallbacks:**

1. **TaskIntelligenceService:**
   - `_build_task_overview_fallback()` — Returns count + priority summary
   - `_build_rule_based_fallback()` — Returns full intelligence JSON with rules-based logic

2. **TaskGenerationService:**
   - Falls back to per-field rule checks if context aggregation fails

3. **NotificationService:**
   - `_generate_ai_explanation()` returns rule-based explanation if Gemma fails

4. **Dashboard:**
   - Falls back gracefully if any service fails; dashboard still renders with partial data

---

### Database Persistence

**Persisted AI Outputs:**
- **Task.ai_explanation** — Persisted when task generated by TaskGenerationService
- **Notification.detail** — Persisted when alert detected by NotificationService

**No caching, no TTL** — Every request triggers fresh Gemma calls.

---

### Testing Checklist

- [ ] Task generation creates tasks with `ai_explanation` populated
- [ ] Dashboard page renders with AI-generated summary, recommendations, insights
- [ ] Tasks page header shows critical tasks overview one-liner
- [ ] Notifications created with AI-generated detail field
- [ ] Fallback activates gracefully when Gemma unavailable
- [ ] CoordinatorAgent daily_update workflow completes successfully
- [ ] No stale cached intelligence appears

---

### Related Files (Not Modified)

- `app/services/intelligence_service/chatbot_service/prompts/_prompt_task_intelligence.py` — Prompt builders already in place
- `app/models/task.py` — ai_explanation field already defined
- `app/models/notification.py` — detail field already defined
- `app/repositories/task_repository.py` — No changes needed
- `app/repositories/notification_repository.py` — No changes needed

---

## 6. Notification System

> _Architecture and behaviour of the notification pipeline._

<sub>Source: `Info_files/NOTIFICATION_SYSTEM.md`</sub>

### System Overview

This document describes the complete implementation of the notification and AI intelligence system for Smart Farming.

#### Core Components

1. **Notification Model** (`app/models/notification.py`)
   - Types: `info`, `warning`, `critical`, `recommendation`
   - Fields: `id`, `user_id`, `title`, `message`, `detail`, `notification_type`, `is_read`, `created_at`
   - Includes optional entity tracking (`entity_type`, `entity_id`)

2. **AI Model Service** (Modular & Provider-based)
   - Interface: `app/services/ai_model_service/ai_provider_interface.py`
   - Registry: `app/services/ai_model_service/ai_model_service.py`
   - Providers:
     - **GemmaProvider**: Production AI backend (requires Ollama/Gemma)
     - **PlaceholderProvider**: Testing backend (no external dependencies)

3. **Task Intelligence Service** (`app/services/task_intelligence_service.py`)
   - Generates AI-driven insights from task context
   - Caches results for 5 minutes to reduce API calls
   - Falls back to rule-based analysis if AI is unavailable
   - Input: Task status, pending items, weekly plan, seasonal planner, weather data
   - Output: Summary, priority level, recommendations, urgent actions, risks, insights

4. **Task Event Service** (`app/services/task_event_service.py`)
   - Fires in background on task changes (create, update, delete, mark done)
   - Runs task intelligence generation asynchronously
   - Creates `critical` and `recommendation` notifications from results
   - Prevents duplicate notifications within 30-minute window

5. **Notification UI** (`app/templates/notification_ui.html`)
   - Bell icon with red badge showing unread count
   - Dropdown showing all unread notifications
   - Color-coded and symbol-decorated notifications
   - Popup alerts for critical notifications
   - Modal details for critical and recommendation notifications
   - Auto-refreshes every 10 seconds

### Usage

#### Setting Up the Development Environment

##### Option 1: Using Placeholder AI (No External Dependencies)

```bash
export USE_PLACEHOLDER_AI=true
flask run
```

The placeholder provider generates deterministic, realistic responses without requiring Gemma or any external API.

##### Option 2: Using Gemma (Production)

1. Install and run Ollama:
   ```bash
   # Download from https://ollama.ai
   ollama pull gemma3:4b
   ollama serve
   ```

2. Start the app (uses Gemma by default):
   ```bash
   flask run
   ```

You can also configure the Gemma endpoint:
```bash
export GEMMA_API_URL=http://your-ollama-server:11434/api/generate
flask run
```

#### Switching Providers

The system is designed to be provider-agnostic. To add a new AI provider:

1. Create a new provider class inheriting from `AIModelProvider`:

```python
from app.services.ai_model_service.ai_provider_interface import AIModelProvider

class MyCustomProvider(AIModelProvider):
    @property
    def name(self) -> str:
        return "My Custom AI"
    
    def complete(self, prompt: str) -> str:
        # Your implementation here
        return response_text
```

2. Register it in `app/__init__.py`:

```python
def _register_ai_provider():
    from app.services.ai_model_service import ai_model_service
    from app.services.ai_model_service.my_custom_provider import MyCustomProvider
    
    ai_model_service.register_provider(MyCustomProvider())
```

#### Notification Types & Display

| Type | Symbol | Color | Use Case | Behavior |
|------|--------|-------|----------|----------|
| `info` | ℹ️ | Blue | General information | Dropdown only |
| `warning` | ⚠️ | Orange | Important but non-critical | Dropdown only |
| `critical` | 🚨 | Red | Urgent alerts | Popup + Dropdown |
| `recommendation` | 💡 | Green | AI-driven suggestions | Dropdown (clickable for details) |

#### Triggering Task Intelligence

Intelligence is automatically generated when:
- A task is created
- A task is updated
- A task is marked complete
- A task is deleted

Manual trigger (from code):
```python
from app.services.task_event_service import TaskEventService
from flask import current_app

TaskEventService.on_task_change(user_id, current_app._get_current_object())
```

#### Creating Notifications Manually

```python
from app.services.domain_service.notification_service import NotificationService

# Create a simple notification
NotificationService.create(
    user_id=1,
    title="Field Alert",
    message="Soil moisture below threshold",
    notification_type="warning"
)

# Create with AI explanation (critical or recommendation)
NotificationService.create(
    user_id=1,
    title="Critical Action Required",
    message="Irrigation needed immediately",
    notification_type="critical",
    detail="The AI analysis detected that Field A has soil moisture at 15%, "
           "which is below the critical threshold of 20%. Immediate irrigation "
           "is recommended to prevent crop stress."
)

# Prevent duplicates (deduplicates within 30 minutes)
NotificationService.create_if_not_duplicate(
    user_id=1,
    title="Recommendation",
    message="Water Field B",
    notification_type="recommendation",
    within_minutes=30
)
```

#### API Endpoints

##### Get Unread Notifications
```
GET /notifications/unread?user_id=1
```
Response:
```json
{
  "notifications": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Field Alert",
      "message": "Soil moisture below threshold",
      "detail": null,
      "notification_type": "warning",
      "is_read": false,
      "created_at": "2026-04-30T10:30:00",
      "symbol": "⚠️",
      "color": "#FF9800",
      "bg_color": "#FFF3E0",
      "label": "Warning"
    }
  ],
  "unread_count": 1
}
```

##### Get Unread Count
```
GET /notifications/unread/count?user_id=1
```

##### Get Unread Critical Notifications (Alerts)
```
GET /notifications/unread/critical?user_id=1
```

##### Mark as Read
```
PUT /notifications/{id}/read
```

##### Mark All as Read
```
PUT /notifications/read-all?user_id=1
```

##### Get All Notifications (Paginated)
```
GET /notifications/?user_id=1&page=1&per_page=20&type=warning
```

#### Frontend Integration

Include the notification UI in your base template:

```html
{% extends "base.html" %}

{% block content %}
  <!-- Your page content here -->
{% endblock %}
```

The `base.html` template automatically includes `notification_ui.html` which provides:
- Bell icon in header
- Dropdown notifications list
- Automatic unread count update
- Alert popups for critical notifications
- Modal details for alerts and recommendations

#### Context Aggregation for Intelligence

The task intelligence receives a context dict containing:

```python
context = {
    "tasks": {
        "pending_count": int,
        "overdue_count": int,
        "critical_count": int,
        "high_priority_count": int,
        "pending_list": [
            {
                "id": int,
                "title": str,
                "priority": str,
                "due_date": str,
                "is_overdue": bool,
                "field_name": str,
                "crop_name": str,
                "status": str,
            }
        ]
    },
    "farm": {
        "active_fields": int,
        "active_fields_data": [
            {
                "id": int,
                "name": str,
                "moisture_level": float,
                "health_status": str,
                "crop": str,
            }
        ]
    },
    "weather": {
        "current": {
            "temp": float,
            "humidity": float,
            "precipitation": float,
            "condition": str,
        },
        "forecast": [
            {
                "date": str,
                "temp_high": float,
                "temp_low": float,
                "condition": str,
            }
        ]
    },
    "weekly_plan": [...],  # Planned tasks for the week
    "seasonal_plan": [...], # Seasonal schedule
    "alerts": [
        {
            "id": int,
            "message": str,
            "level": str,  # "high", "medium", "low"
        }
    ]
}
```

#### Testing the System

1. **Trigger a task change** (creates recommendations):
   ```bash
   curl -X POST http://localhost:5000/mytasks/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "Water Field A", "priority": "high"}'
   ```

2. **Check notifications**:
   ```bash
   curl http://localhost:5000/notifications/unread
   ```

3. **View in browser**:
   - Navigate to any page
   - Click the 🔔 bell icon
   - See notifications in dropdown
   - Critical notifications appear as popups
   - Click alerts/recommendations to see detailed explanations

#### Architecture Decisions

##### Provider Pattern
The modular provider architecture allows:
- Swapping providers with a single line change
- Testing without external dependencies
- Supporting multiple AI backends
- Environment-based provider selection

##### Background Processing
- Task intelligence runs asynchronously in a daemon thread
- HTTP responses never blocked by AI calls
- Notifications created from intelligence results
- Deduplication prevents notification spam

##### Caching
- 5-minute cache on task intelligence
- Invalidated on task changes
- Reduces load on AI provider
- Maintains freshness for rapidly changing data

##### Notification Model
- Supports multiple types with extensible metadata
- Optional detail field for rich explanations
- Entity tracking enables future drill-down
- `is_read` status enables badge counting

### Troubleshooting

#### Notifications Not Appearing

1. Check that notifications are being created:
   ```bash
   curl http://localhost:5000/notifications/unread
   ```

2. Verify user_id is correct (currently hardcoded as 1)

3. Check browser console for JavaScript errors

#### AI Provider Not Working

1. Check provider registration:
   ```python
   from app.services.ai_model_service import ai_model_service
   print(ai_model_service.get_provider().name)
   ```

2. For Gemma: Ensure Ollama is running
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Use placeholder provider for testing:
   ```bash
   export USE_PLACEHOLDER_AI=true
   ```

#### Performance Issues

1. Check cache TTL settings in `task_intelligence_service.py`
2. Reduce notification refresh interval in `notification_ui.html`
3. Implement Redis-backed cache for multi-worker deployments

### Next Steps

- [ ] Replace hardcoded `USER_ID = 1` with auth session integration
- [ ] Add push notifications for critical alerts
- [ ] Implement notification scheduling (e.g., quiet hours)
- [ ] Add notification preferences UI
- [ ] Create admin dashboard for notification management
- [ ] Set up notification analytics
- [ ] Implement real-time notifications with WebSockets

---

## 7. Notification Testing

> _Test procedures, scenarios, and verification steps for the notification system._

<sub>Source: `Info_files/NOTIFICATION_TESTING.md`</sub>

### Quick Test

#### 1. Start the app with placeholder AI (no external dependencies)
```bash
export USE_PLACEHOLDER_AI=true
flask run
```

#### 2. Create a test notification
```bash
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Test Alert",
    "message": "This is a test notification",
    "notification_type": "critical",
    "detail": "This is the detailed explanation shown when clicked"
  }'
```

#### 3. Check the notification appears
- Navigate to http://localhost:5000 (or any page)
- Look for red 🔔 bell in header
- Should show "1" badge
- Click bell to open dropdown
- Should see your notification with 🚨 symbol

#### 4. Test marking as read
- Click on the notification in the dropdown
- Should show modal with title and detail
- Click "Close" button
- Badge count should decrease
- Reload page - notification should still be marked read

#### 5. Test critical alert popup
- Create another critical notification with notification_type="critical"
- Should pop up in top-right corner
- Auto-dismisses after 10 seconds
- Marked as read, so won't show again on refresh

### Testing Different Notification Types

```bash
# Info notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "info", "title": "Info", "message": "This is info"}'

# Warning notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "warning", "title": "Warning", "message": "This is a warning"}'

# Recommendation notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "recommendation", "title": "Recommendation", "message": "Water Field A", "detail": "AI recommends watering based on soil moisture data"}'
```

### Test Multi-Tab Behavior

1. Open the app in two browser tabs
2. Create a notification in one tab
3. Both tabs should see the notification (auto-refresh every 10s)
4. Click mark as read in tab 1
5. Tab 2 should update within 10 seconds
6. Reload page 2 - notification should stay marked as read

### Troubleshooting

#### Notification Bell Not Working

**Problem**: Bell doesn't respond to clicks

**Solutions**:
1. Check browser console for JavaScript errors (F12 → Console tab)
2. Verify notification-ui.html is included in your template
3. Check that `notification-container` div exists
4. Try hard refresh (Ctrl+F5 or Cmd+Shift+R)

#### Notifications Disappear on Refresh

**Problem**: Marked notifications reappear as unread after page reload

**Solutions**:
1. Check database connectivity: `sqlite3 instance/smartfarming.db "SELECT * FROM notification;"`
2. Verify NotificationService.mark_as_read() is being called
3. Check for errors in Flask logs
4. Clear browser cache: Ctrl+Shift+Delete, select "All time", clear

#### Duplicate Notifications

**Problem**: Same notification appears multiple times

**Solutions**:
1. This is by design - duplicate detection uses 30-minute window
2. To change: edit `task_event_service.py` and `create_if_not_duplicate()` call
3. Or use `NotificationService.create()` instead of `create_if_not_duplicate()`

#### Alerts Not Popping Up

**Problem**: Critical notifications don't show as popups

**Solutions**:
1. Ensure notification_type is exactly "critical"
2. Check that notification is marked `is_read=false`
3. Verify alertsContainer div exists in page
4. Check browser console for JavaScript errors

#### Multiple Instances Running

**Problem**: Bell doesn't work on all pages / works only once

**Fixed by**: Updated initialization to check for existing instance and prevent duplicates

If you still have issues:
1. Check `window.notificationSystem` in browser console - should exist
2. If not, check for JavaScript errors preventing initialization
3. Try clearing browser storage: `localStorage.clear()` in console

### API Reference

#### Create Test Notification
```
POST /notifications/test/create
Body: {
  "user_id": 1,
  "title": "Title",
  "message": "Message",
  "notification_type": "critical|warning|info|recommendation",
  "detail": "Optional detailed explanation"
}
```

#### Get Unread Notifications
```
GET /notifications/unread?user_id=1
```

#### Mark as Read
```
PUT /notifications/{id}/read
```

#### Mark All as Read
```
PUT /notifications/read-all?user_id=1
```

#### Get by Type
```
GET /notifications/?user_id=1&type=critical&page=1&per_page=20
```

### Key Fixes Applied

1. **Single Instance** - Only one NotificationSystem instance created globally
2. **Event Listener Cleanup** - Removed duplicate event listeners on re-init
3. **Error Handling** - Try-catch blocks around all DOM operations
4. **Read Status Persistence** - Immediately update local state before API call
5. **Alert Queue Management** - Track shown alerts to prevent duplicates
6. **localStorage Backup** - Persist shown alert IDs to survive page refresh
7. **Dropdown Rendering** - Clone and replace items to avoid listener conflicts

### Performance Tips

- Notifications refresh every 10 seconds (configurable in notification_ui.html)
- Change: `NOTIFICATION_CONFIG.updateInterval = 5000` for 5-second refresh
- Task intelligence caches for 5 minutes to reduce load
- Consider Redis cache for multi-worker deployments

---

## 8. Component Template

> _Reusable component conventions and templating standards for the frontend._

<sub>Source: `Info_files/COMPONENT_TEMPLATE.md`</sub>

This document provides the standardized header and navigation bar components for use across all pages in the Climate Adaptation Planner project.

### Tailwind Configuration

Add this to every new page's `<head>` section (in a `<script id="tailwind-config">` tag):

```javascript
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      "colors": {
        "surface": "#fcf9f0",
        "secondary-fixed": "#d5e9c1",
        "on-error-container": "#93000a",
        "inverse-primary": "#bbccaa",
        "on-tertiary-fixed": "#1e1c12",
        "tertiary-fixed-dim": "#ccc6b6",
        "surface-container-high": "#ebe8df",
        "primary": "#47573b",
        "on-secondary-fixed-variant": "#3b4b2e",
        "secondary-fixed-dim": "#bacda7",
        "surface-dim": "#dddad1",
        "surface-variant": "#e5e2da",
        "on-secondary-fixed": "#111f07",
        "surface-container-highest": "#e5e2da",
        "on-tertiary-container": "#f1ebda",
        "on-secondary-container": "#586a4a",
        "inverse-on-surface": "#f4f1e8",
        "on-primary": "#ffffff",
        "on-primary-fixed": "#121f09",
        "on-primary-container": "#dff1cd",
        "secondary-container": "#d5e9c1",
        "background": "#fcf9f0",
        "on-surface": "#1c1c17",
        "outline": "#75786f",
        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "primary-container": "#5f6f52",
        "tertiary-container": "#6e6a5d",
        "surface-container-low": "#f7f3ea",
        "tertiary": "#555246",
        "on-surface-variant": "#444840",
        "error-container": "#ffdad6",
        "on-tertiary-fixed-variant": "#4a473b",
        "primary-fixed": "#d6e8c5",
        "primary-fixed-dim": "#bbccaa",
        "on-primary-fixed-variant": "#3c4b31",
        "tertiary-fixed": "#e8e2d2",
        "inverse-surface": "#31312b",
        "surface-bright": "#fcf9f0",
        "surface-container-lowest": "#ffffff",
        "secondary": "#536344",
        "surface-container": "#f1eee5",
        "on-secondary": "#ffffff",
        "on-tertiary": "#ffffff",
        "surface-tint": "#536347",
        "outline-variant": "#c5c8bd",
        "on-background": "#1c1c17"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "1.5rem",
        "full": "9999px"
      },
      "fontFamily": {
        "headline": ["Manrope"],
        "body": ["Work Sans"],
        "label": ["Work Sans"]
      }
    },
  },
}
```

### Theme Initialization Script

Add this to the `<head>` section before any other scripts:

```html
<script>
  // Initialize theme immediately to avoid flickering
  (function() {
    const theme = localStorage.getItem('theme') || 'light';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  })();
</script>
```

### Standard Header Component

```html
<!-- TopAppBar Section -->
<header class="bg-[#fcf9f0] dark:bg-[#1c1c17] flex justify-between items-center w-full px-6 py-4 sticky top-0 z-50">
  <div class="flex items-center gap-3">
    <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]" style="font-size: 28px;">agriculture</span>
    <h1 class="text-2xl font-semibold text-[#47573b] dark:text-[#d5e9c1] font-['Manrope'] tracking-tight">Climate Adaptation Planner</h1>
  </div>
  <div class="flex gap-4">
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="toggleTheme()" id="themeToggle">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">brightness_4</span>
    </button>
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="showNotifications()">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">notifications</span>
    </button>
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="openSearch()">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">search</span>
    </button>
  </div>
</header>
```

### Standard Navigation Bar Component

**Note:** The active nav item should match the current page.

```html
<!-- BottomNavBar Section -->
<nav class="fixed bottom-0 left-0 w-full z-50 bg-[#fcf9f0]/80 dark:bg-stone-950/80 backdrop-blur-md rounded-t-[24px] shadow-[0_-8px_24px_rgba(28,28,23,0.06)] flex justify-around items-center px-4 pb-6 pt-3">
  <!-- Dashboard (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/dashboard">
    <span class="material-symbols-outlined" data-icon="dashboard">dashboard</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Dashboard</span>
  </a>

  <!-- Fields (active on fields.html) -->
  <a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/myfields">
    <span class="material-symbols-outlined" data-icon="landscape" style="font-variation-settings: 'FILL' 1;">landscape</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Fields</span>
  </a>

  <!-- Crops (active on crops.html) -->
  <a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/mycrops">
    <span class="material-symbols-outlined" data-icon="eco" style="font-variation-settings: 'FILL' 1;">eco</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Crops</span>
  </a>

  <!-- Tasks (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/mytasks">
    <span class="material-symbols-outlined" data-icon="assignment_turned_in">assignment_turned_in</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Tasks</span>
  </a>

  <!-- Planner (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/myplanner">
    <span class="material-symbols-outlined" data-icon="calendar_today">calendar_today</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Planner</span>
  </a>

  <!-- Chat (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="#">
    <span class="material-symbols-outlined" data-icon="chat">chat</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Chat</span>
  </a>
</nav>
```

### Theme Toggle Functions

Add these JavaScript functions to your page:

```javascript
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

function toggleTheme() {
  const html = document.documentElement;
  if (html.classList.contains('dark')) {
    html.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  } else {
    html.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  }
}

// Initialize theme on page load
initTheme();
```

### CSS Requirements

Every page must link to the base CSS file for semantic utilities:
- Link `fields.css` or `crops.css` (which imports `base.css`)

The base.css provides:
- **CSS Variables** for light mode (default) and dark mode
- **Semantic Utility Classes** like `.bg-secondary-fixed`, `.text-on-background`, etc.
- **Color Theme Overrides** that automatically apply when `.dark` class is on html element

### Navigation Bar Details

#### Color Scheme by Theme:
- **Light Mode (Default):**
  - Background: #fcf9f0 (light cream)
  - Active tab: #d5e9c1 (light green) background
  - Text: #47573b (dark green)
  
- **Dark Mode:**
  - Background: stone-950 (very dark)
  - Active tab: #47573b (green) background
  - Text: #fcf9f0 (light cream)

#### How to Mark a Tab Active:
Replace the inactive `<a>` tag with the active version:
```html
<!-- Inactive -->
<a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 ...">

<!-- Active (add these classes: bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl) -->
<a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 ...">
```

### Best Practices

1. Always include the theme initialization script in `<head>` before other scripts
2. Always include the Tailwind config to ensure consistent styling
3. Always link the CSS file (fields.css or crops.css) which imports base.css
4. Use semantic utility classes from base.css instead of hardcoded hex values
5. Use the `.dark` class for dark mode (controlled by JavaScript)
6. Test theme toggle on each new page before deployment

---

## 9. Frontend Verification

> _Manual / scripted verification routines for the frontend integration._

<sub>Source: `Info_files/FRONTEND_VERIFICATION.md`</sub>

### ✅ Files Updated

#### HTML Pages with Notification UI
- ✅ `app/templates/crops.html` - Added notification UI to header
- ✅ `app/templates/fields.html` - Added notification UI to header  
- ✅ `app/templates/tasks.html` - Replaced old notification system with new UI
- ✅ `app/templates/notification_ui.html` - Fixed all JavaScript issues
- ✅ `app/templates/base.html` - Base template with integrated notifications

#### Backend Files Updated
- ✅ `app/__init__.py` - Added environment variable support for AI provider selection
- ✅ `app/schemas/notification_schema.py` - Added color, symbol, and metadata
- ✅ `app/routes/notifications.py` - Added test endpoint for creating notifications
- ✅ `app/services/ai_model_service/placeholder_provider.py` - Test AI provider

### 🧪 Step-by-Step Test

#### 1. Start the App
```bash
export USE_PLACEHOLDER_AI=true
flask run
```

#### 2. Navigate to Any Page
- Go to `http://localhost:5000/mycrops` or `/myfields` or `/mytasks`
- Look at the header - you should see a **bell icon 🔔** next to the theme toggle

#### 3. Create Test Notifications
```bash
# Create an INFO notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "info", "title": "Info Test", "message": "This is an info message"}'

# Create a WARNING notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "warning", "title": "Warning Test", "message": "This is a warning message"}'

# Create a CRITICAL notification (will pop up)
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "critical", "title": "Critical Alert", "message": "This is critical!", "detail": "Detailed explanation of the critical issue"}'

# Create a RECOMMENDATION notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "recommendation", "title": "AI Recommendation", "message": "Water Field A", "detail": "Based on soil moisture analysis, Field A needs irrigation"}'
```

#### 4. Test Bell Icon
- **Before notifications**: Bell should be grey 🔔
- **After notifications**: Bell should turn **red** 🔔 with a **count badge**
- **Hover**: Bell should change color

#### 5. Test Dropdown
- **Click bell icon** → Dropdown should appear below
- **Multiple clicks** → Should work smoothly (no errors)
- **Click outside** → Dropdown closes
- **See notifications** → All notifications should be listed with:
  - ℹ️ symbol for info (blue)
  - ⚠️ symbol for warning (orange)
  - 🚨 symbol for critical (red)
  - 💡 symbol for recommendations (green)
  - Time indicator (e.g., "just now", "5m ago")
  - Blue dot for unread notifications

#### 6. Test Alert Popups (Critical Only)
- **Create critical notification** (see step 3)
- **Page should auto-refresh**
- **Top-right popup** should appear with 🚨 Alert
- **Auto-disappears** after 10 seconds
- **Manual close** by clicking ✕ button

#### 7. Test Modal Details
- **Click on alert/recommendation** in dropdown
- **Modal should pop up** with:
  - Title at top
  - Detailed explanation
  - Close button
- **Click outside modal** → closes
- **Click Close button** → closes

#### 8. Test Mark as Read
- **Click notification in dropdown**
- Shows detail modal
- **After closing**: notification disappears from dropdown
- **Badge count decreases**
- **Reload page**: notification stays marked as read ✅

#### 9. Test Multi-Tab Behavior
- **Open 2 browser tabs** to same page
- **Create notification in tab 1**
- **Tab 2 auto-updates** within 10 seconds
- **Mark as read in tab 1**
- **Tab 2 reflects change** within 10 seconds

#### 10. Test Mark All as Read
- **Click "Mark all as read"** button in dropdown header
- **All notifications disappear**
- **Badge disappears**
- **Reload page**: stays cleared ✅

### ✅ Expected Behavior

#### Bell Icon States
| State | Appearance |
|-------|-----------|
| No notifications | Grey 🔔 |
| Has unread | Red 🔔 with count |
| Hovered | Darker color |

#### Notification Display
| Type | Symbol | Color | Display |
|------|--------|-------|---------|
| Info | ℹ️ | Blue | Dropdown only |
| Warning | ⚠️ | Orange | Dropdown only |
| Critical | 🚨 | Red | Popup + Dropdown |
| Recommendation | 💡 | Green | Dropdown (clickable) |

#### Interactions
| Action | Result |
|--------|--------|
| Click bell | Dropdown opens/closes |
| Click notification | Shows modal detail (for critical/recommendation) |
| Mark as read | Removes from unread, badge updates |
| Mark all read | Clears all, badge disappears |
| Click outside | Dropdown closes |
| Page refresh | Notifications stay marked correctly |

### 🐛 Troubleshooting

#### Bell doesn't appear
1. Check page includes `notification_ui.html` - should be in header
2. Verify template is using Jinja2 (`.html` extension, not `.jinja2`)
3. Check browser console for errors (F12 → Console)

#### Dropdown doesn't open
1. Check browser console for JavaScript errors
2. Verify `window.notificationSystem` exists in console
3. Check that notification container exists: `document.getElementById('notification-container')`

#### Only works once
1. **Fixed!** - All event listeners now properly managed
2. If still happening, clear browser cache (Ctrl+Shift+Delete)
3. Check console for JavaScript errors

#### Notifications revert to unread after refresh
1. **Fixed!** - localStorage now persists shown alerts
2. Check browser allows localStorage: `localStorage.setItem('test', 'test')`

#### Alerts don't popup
1. Ensure notification_type is exactly `"critical"`
2. Check is_read is `false`
3. Verify alertsContainer div exists in page
4. Create new alert - it should popup once

#### Dark mode doesn't work
1. HTML pages set dark mode on root element
2. Check `:root.dark` CSS class is being used
3. Verify `.dark` class is added to `<html>` tag

### 📱 Browser Support
- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile browsers: ✅ Full support (responsive)

### ✨ Next Steps
1. Connect to real AI provider (switch from placeholder)
2. Add push notifications for mobile
3. Implement notification preferences UI
4. Add notification scheduling (quiet hours)
5. Set up real-time WebSocket updates
