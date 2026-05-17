
## 📁 Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone http://github.com/your-username/AgriGemma.git
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

It injects a fake weather-change scenario for a set of test users (covering no-impact, rainfall-impact, and temperature-impact cases), then runs the full coordinator pipeline — rescheduling affected tasks, regenerating the weekly plan, and producing change-summary notifications. Watch the terminal output to see each user's adaptation result. Of course, all of the changes are reflected on the frotnend of the application as well.


## 📦 Requirements
- Python 3.10+
- pip
- [Ollama](https://ollama.com/download) — required for local AI inference (Options A and B); after installing, run `ollama pull gemma4`
- [Google AI Studio API key](https://aistudio.google.com/apikey) — free, required for Option A (cloud chatbot)
- [OpenWeatherMap API key](https://openweathermap.org/api) — free tier is sufficient

## ⚡ Quick Start
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python run.py
```
