
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
flask db migrate -m "initial"
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
http://127.0.0.1:5000/dashboard
```


## 📦 Requirements
- Python 3.8+
- pip
- Virtualenv (recommended)

## ⚡ Quick Start
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python run.py
```
