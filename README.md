# SmartFarming; Climate Adaptation Advisor for Farmers

A smart farming assistant that helps farmers adapt to climate change using weather data, soil conditions, crop monitoring, and AI-driven recommendations.

## 🌍 Problem

Due to **climate change and global warming**, traditional farming calendars and practices are no longer reliable. Farmers face:

- Unpredictable rainfall
- Heatwaves and droughts
- Shifting planting seasons
- Reduced crop yields

This creates economic risk and uncertainty.


## 💡 Solution

A **mobile-first, multilingual farming assistant** that:

### 📥 Inputs
- Weather data (current + forecast)
- Soil information
- Farm details (land size, crops, planting dates)
- Crop photos (for health analysis)

### 📤 Outputs
- Season plans and timelines
- Climate-aware planting decisions
- Best farming practices
- Real-time plan adjustments
- Tasks, alerts, and notifications
- Chatbot support for farmer questions


## 👨‍🌾 Target Users

- Small to medium-scale farmers
- Low to moderate literacy levels
- Limited technical experience
- Mobile users (especially Android)
- Need simple, visual, multilingual tools



## ⚙️ Core Features

### 🏡 Farm Overview
- Land size
- Fields
- Active crops
- Basic farm info

### 🌦️ Weather & Forecast
- Current weather
- Short-term forecast
- Climate-based alerts

### 🌱 Crop Monitoring
- Growth stage tracking
- Health status
- Yield estimates
- Pest/disease alerts

### 🌾 Soil Conditions
- Moisture
- Temperature
- pH (optional)

### ✅ Tasks & Alerts (Key Feature)
- Daily actionable tasks
- Climate-based alerts
- Simple instructions (e.g., irrigate, fertilize)

### 📅 Season Planner
- Planting → growing → harvesting timeline
- Adaptive planning based on weather

### 🤖 Chatbot Assistant
- Ask questions
- Get farming advice
- Handle "what-if" scenarios



## 🧠 Key Value

This app transforms:

> **Weather data → Practical farming decisions**

It acts as a **daily farming companion**, not just a data dashboard.


## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** JavaScript (mobile-friendly)
- **Database:**  PostgreSQL 
- **APIs:** Weather APIs, agriculture data APIs
- **AI (optional):**
  - Crop image analysis
  - Recommendation engine
  - Chatbot integration


## 📁 Project Structure

```bash
climate-adaptation-advisor/
│
├── app/
│ ├── static/
│ ├── templates/
│ ├── routes/
│ ├── services/
│ ├── models/
│ ├── utils/
│ └── __init__.py
│
├── instance/
├── config.py
├── run.py
├── requirements.txt
└── README.md
