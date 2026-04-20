# AgriGemma: A Climate-Smart Seasonal Planner for Smallholder Farmers

A smart farming assistant that helps farmers adapt to climate change using weather data, soil conditions, crop monitoring, and AI-driven recommendations.

## 🌍 Problem

Due to **climate change and global warming**, traditional farming calendars and practices are no longer reliable. Farmers face:

- Unpredictable rainfall
- Heatwaves and droughts
- Shifting planting seasons
- Reduced crop yields

This creates economic risk and uncertainty.

---

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

AgriGemma uses Gemma 4 to generate crop schedules and adapt them in real time when climate conditions change, helping farmers make safer planting, irrigation, and harvest decisions. Gemma 4 acts as the decision explainer and planner orchestrator, not as a raw weather predictor. 

###### Gemma 4 as an adaptive climate-planning agent for agriculture.

---

## 👨‍🌾 Target Users

- Small to medium-scale farmers
- Low to moderate literacy levels
- Limited technical experience
- Mobile users (especially Android)
- Need simple, visual, multilingual tools

---

## Limits

prototype uses simplified agronomy rules
forecast quality affects advice quality
recommendations should support, not replace, local agronomists
regional calibration is needed for deployment

---

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

---

## 🧠 Key Value

This app transforms:

> **Weather data → Practical farming decisions**

It acts as a **daily farming companion**, not just a data dashboard.

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** JavaScript (mobile-friendly)
- **Database:**  PostgreSQL 
- **APIs:** Weather APIs, agriculture data APIs
- **AI:**
  - Recommendation engine
  - Chatbot integration
    
---

## 📁 Project Structure

```bash
smart-farming/
│
├── app/
│   ├── __init__.py          # App factory
│   │
│   ├── routes/             # All API & page routes
│   │   ├── __init__.py
│   │   ├── main.py         # Home/dashboard
│   │   ├── fields.py       # Fields management
│   │   ├── crops.py        # Crop monitoring
│   │   ├── tasks.py        # Tasks & alerts
│   │   ├── weather.py      # Weather endpoints
│   │   └── chatbot.py      # AI chatbot
│   │
│   ├── models/             # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── field.py
│   │   ├── crop.py
│   │   ├── task.py
│   │   └── alert.py
│   │
│   ├── services/           # Core logic (VERY IMPORTANT)
│   │   ├── weather_service.py
│   │   ├── crop_service.py
│   │   ├── soil_service.py
│   │   ├── recommendation_service.py
│   │   ├── gemma_service.py
│   │   ├── task_service.py
│   │   └── chatbot_service.py
│   │
│   ├── templates/          # HTML (if using server-side rendering)
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── fields.html
│   │   └── crops.html
│   │
│   ├── static/             # CSS, JS, images
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   │
│   ├── utils/              # Helpers
│   │   ├── helpers.py
│   │   ├── constants.py
│   │   └── validators.py
│   │
│   └── extensions.py       # DB, migrate, etc.
│
├── instance/               # Instance-specific configs
│
├── migrations/             # DB migrations
│
├── config.py               # App config
├── run.py                  # Entry point
├── requirements.txt
├── .env
└── README.md
```

---

## 📁 Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone http://github.com/your-username/smart-farming.git
cd smart-farming
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
Create a .env file in the root directory:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
WEATHER_API_KEY=your_weather_api_key
DATABASE_URL=sqlite:///app.db
```

### 6. Initialize the Database (Optional)
```bash
flask db init
flask db migrate
flask db upgrade
```
Skip this step if database migrations are not configured.

### 7. Run the Application
```bash
python run.py
```
OR

```bash
flask run
```

### 8. Open in Browser
```bash
http://127.0.0.1:5000/
```


## 📦 Requirements
- Python 3.8+
- pip
- Virtualenv (recommended)

## ⚡ Quick Start
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python run.py
```

---

## 🌍 Hackathon Context

This project is developed as part of the:

### 🏆 Gemma 4 Good Hackathon (Kaggle)

The hackathon focuses on building impactful AI-powered solutions that address real-world problems and create social good.

---

## 🎯 Our Contribution

We are tackling a critical global issue:

- Climate change disrupting traditional farming practices  
- Increasing uncertainty in crop planning and yields  
- Economic risk for small and medium-scale farmers  

### 💡 What We Built

A **Climate Adaptation Advisor for Farmers** — a mobile-first, multilingual assistant that:

- Converts weather and climate data into actionable farming decisions  
- Helps farmers plan, adapt, and respond in real time  
- Provides simple, easy-to-understand guidance for non-technical users  

---

## 🧠 Key Innovation

- Combines **climate data + farm data + AI**
- Supports **multimodal inputs** (text, weather, images)
- Provides **real-time adaptive recommendations**
- Focuses on **low-literacy, accessibility-first design**

---

## 🧪 Example Workflow

1. Farmer inputs:
   - Farm location  
   - Land size  
   - Crop type  
   - Planting date  
   - Soil details  

2. System processes:
   - Weather and forecast data  
   - Soil and crop conditions  
   - Climate risks  

3. Application outputs:
   - Season plan and timeline  
   - Recommended farming actions  
   - Tasks and alerts  
   - Real-time adaptive suggestions  

4. Farmer interacts:
   - Completes tasks  
   - Receives alerts  
   - Uses chatbot for assistance  

---

## 🎯 Design Principles

This application is built with:

- **Simplicity first** — designed for non-technical users  
- **Mobile-first UI** — optimized for smartphones  
- **Visual communication** — icons, colors, minimal text  
- **Action-driven** — every insight leads to a clear task  
- **Multilingual-ready** — adaptable to local languages  

---

## 🔮 Future Improvements

- Voice assistant for low-literacy users
- Crop Image Analysis 
- Regional language support  
- Offline functionality for rural areas  
- Satellite-based crop monitoring  
- Advanced crop disease detection  
- SMS / WhatsApp alert system  
- Yield prediction and economic insights  

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository  
2. Create a new branch  
3. Make your changes  
4. Commit your updates  
5. Open a pull request  

---

## 📄 License

This project is licensed under the MIT License.

---

## ✨ Authors

Atqa R. Amir, Amna Bukhari, Syed Faizan

Built to support **climate-resilient farming** through simple, practical, and accessible technology.
Developed for the **Gemma 4 Good Hackathon (Kaggle)**.



