
# AgriGemma

## 📁 Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AgriGemma.git
cd AgriGemma
```

### 2. Create a virtual env
```bash
python -m venv venv
```

### 3. Activate the virtual env

```bash
venv\Scripts\activate
```
### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Up Environment Variables
Create a `.env` file in the root directory:

```env
FLASK_APP=run.py
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///app.db

# ── Weather ────────────────────────────────────────────────────────────────────
WEATHER_API_KEY=your_openweather_api_key

# ── AI Provider ────────────────────────────────────────────────────────────────
# Choose ONE of the three modes below:

# Option A — RECOMMENDED — Google AI Studio (cloud chatbot) + Ollama local (background tasks)
# Get a free key at https://aistudio.google.com/apikey
USE_GOOGLE_AI=true
GOOGLE_API_KEY=your_google_ai_key
GOOGLE_AI_MODEL=gemma-4-26b-a4b-it   # or gemma-4-31b-it for highest quality

# Option B — Ollama only (fully offline, no API key needed)
# USE_GOOGLE_AI=false
# (Ollama settings below are also used for background tasks in Option A)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4          # gemma4:e2b (lighter) or gemma4:26b (highest quality)

# Option C — Placeholder responses (no AI required, for UI testing)
# USE_PLACEHOLDER_AI=true

# Option D — LiteRT (fully offline, on-device, no Ollama needed)
# Requires mediapipe>=0.10.21 and the Gemma 4 1B model file (~2 GB)
# Download model from: https://www.kaggle.com/models/google/gemma-4/litert/gemma4-1b-it-gpu-int4
# Place at: ~/.gemma_models/gemma4-1b-it-gpu-int4.task  (or set GEMMA_MODEL_PATH)
# USE_LITERT=true
# GEMMA_MODEL_PATH=/path/to/gemma4-1b-it-gpu-int4.task   # optional, overrides default
```

> **Tip:** `FLASK_ENV` is not required. For Ollama (Option A or B), install from https://ollama.com/download then run `ollama pull gemma4`.

### 6. Initialize the Database (Optional)
```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```
Skip this step if database migrations are not configured.

### 7. Run the Application
```bash
python run.py
```

> **Note:** `test_runs/seed_data.py` runs automatically on every startup — it wipes and recreates the database with a full set of demo farmers, fields, crops, tasks, weather records, and plans. No manual seeding step is needed.

### 8. Open in Browser
```bash
http://127.0.0.1:5000/
```

---

## 🌦️ Testing Weather Adaptation

AgriGemma's core feature is **automatic adaptation** of tasks and weekly plans when weather conditions change. The script `test_runs/test_task_changes.py` simulates this end-to-end:

```bash
python test_runs/test_task_changes.py
```
It injects a fake weather-change scenario for a set of test users (covering no-impact, rainfall-impact, and temperature-impact cases), then runs the full coordinator pipeline — rescheduling affected tasks, regenerating the weekly plan, and producing change-summary notifications. Watch the terminal output to see each user's adaptation result. Of course, all of the changes are reflected on the frontend of the application as well.
It takes about ~40seconds for a popup toasts appears on the screen, along with the notifications.


## 📦 Requirements
- Python 3.10+
- pip
- [Ollama](https://ollama.com/download) — required for local AI inference (Options A and B); after installing, run `ollama pull gemma4`
- [Google AI Studio API key](https://aistudio.google.com/apikey) — free, required for Option A (cloud chatbot)
- [OpenWeatherMap API key](https://openweathermap.org/api) — free tier is sufficient
- **Option D only:** `mediapipe>=0.10.21` (included in requirements.txt) + Gemma 4 1B `.task` model file downloaded from Kaggle

## ⚡ Quick Start

**Windows:**
```bash
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python run.py
```

**Mac/Linux:**
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python run.py
```

---

## 🛠️ Troubleshooting

#### "Connection refused on port 11434"
Ollama is not running. Start it:
```bash
ollama serve
```
Wait 3–5 seconds for the server to initialize, then retry.

#### "Model not found"
The model hasn't been pulled yet:
```bash
ollama pull gemma4
```

#### Slow responses
- First request after starting Ollama is always slower (model loads into memory).
- If consistently slow, switch to a lighter model: set `OLLAMA_MODEL=gemma4:e2b` in `.env`.

#### "AI model failed: HTTPConnectionPool..."
Ollama crashed or stopped. Restart it:
```bash
ollama serve
```

#### No AI responses at all (UI testing mode)
To run without any AI backend, set in `.env`:
```env
USE_PLACEHOLDER_AI=true
```

#### Debugging Flask startup
Set `FLASK_DEBUG=1` in `.env` to enable debug logging and see which AI provider initialized:
```env
FLASK_DEBUG=1
```
Look for lines like `✅ Google AI initialized` or `✅ Ollama connected` in the output.

---

## 💻 Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| RAM | 4 GB minimum, 8 GB recommended |
| Disk | 10 GB free (for Ollama model + cache) |
| CPU | Modern multi-core (ARM/x86) |
| GPU | Optional — improves Ollama inference speed |
| Internet | Required for Option A (Google AI) and initial Ollama model pull |

---

## 🧹 Cleanup

#### Remove Ollama model cache
```bash
# Windows
rmdir /s %USERPROFILE%\.ollama\models

# Unix/Mac
rm -rf ~/.ollama/models
```
The model will re-download from Ollama on next use.

#### Reset the database
Delete `app.db` in the project root, then restart the app — `seed_data.py` will recreate it automatically.

---

## 🔀 Migration Guides

### Switching AI Provider

All three options are controlled entirely by `.env` — no code changes needed. Stop the app, update `.env`, and restart.

#### Option B → Option A (add Google AI for chatbot)
```env
USE_GOOGLE_AI=true
GOOGLE_API_KEY=your_google_ai_key
GOOGLE_AI_MODEL=gemma-4-26b-a4b-it
# Keep OLLAMA_HOST and OLLAMA_MODEL — still used for background tasks
```

#### Option A → Option B (go fully offline)
```env
USE_GOOGLE_AI=false
# GOOGLE_API_KEY can be removed or left — it won't be used
```

#### Any option → Option C (placeholder, no AI)
```env
USE_PLACEHOLDER_AI=true
```

#### Option C → any real provider
Remove `USE_PLACEHOLDER_AI` (or set it to `false`), then configure Option A, B, or D as above.

#### Any option → Option D (LiteRT, fully offline on-device)

**Step 1:** Ensure mediapipe is installed (already in requirements.txt):
```bash
pip install "mediapipe>=0.10.21"
```

**Step 2:** Download the Gemma 4 1B model from Kaggle:
```
https://www.kaggle.com/models/google/gemma-4/litert/gemma4-1b-it-gpu-int4
```
Place the `.task` file at `~/.gemma_models/gemma4-1b-it-gpu-int4.task`, or set `GEMMA_MODEL_PATH` to a custom path.

**Step 3:** Update `.env`:
```env
USE_LITERT=true
# Remove or comment out USE_GOOGLE_AI and USE_PLACEHOLDER_AI
# GEMMA_MODEL_PATH=/custom/path/gemma4-1b-it-gpu-int4.task  # optional
```

> **Note:** If the model file is missing when `USE_LITERT=true` is set, the app logs an `ERROR` at startup and falls back to placeholder responses — check the terminal output if responses seem generic.

#### Option D → Ollama (switch to local server-based inference)

**Step 1:** Install Ollama and pull the model:
```bash
ollama pull gemma4
```

**Step 2:** Update `.env`:
```env
USE_LITERT=false
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4
```

**Step 3:** Start Ollama before running the app:
```bash
ollama serve
```

### Database Migrations

Flask-Migrate (Alembic) is used to manage schema changes. Run these whenever models change.

#### Apply existing migrations (after pulling new code)
```bash
flask db upgrade
```

#### Create a new migration after changing a model
```bash
flask db migrate -m "describe what changed"
flask db upgrade
```

#### Roll back the last migration
```bash
flask db downgrade
```

#### Check current migration state
```bash
flask db current   # active revision
flask db history   # full migration log
```

> **Note:** The app uses SQLite by default (`app.db`). For a clean slate, delete `app.db` and restart — `seed_data.py` repopulates everything automatically, so you only need migrations when preserving existing data.
