from datetime import date, datetime, timedelta

import json

from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.models.crop import Crop
from app.models.field import Field
from app.models.task import Task
from app.models.alert import Alert
from app.models.weather import Weather
from app.models.weather_forecast import WeatherForecast
from app.models.seasonal_plan import SeasonalPlan, SeasonalPlanEntry
from app.models.weekly_plan import WeeklyPlan, WeeklyPlanEntry
from app.models.plan_event_override import PlanEventOverride
from app.models.chat import Conversation, ChatMessage
from app.models.dashboard_summary import DashboardSummary
from app.models.task_intelligence_summary import TaskIntelligenceSummary
from sqlalchemy import text

from app.utils import clock


# Every demo table, children before parents, so the clear also works on databases
# that enforce foreign keys (Postgres). Vocabulary and rulebook tables are not here:
# they are upserted / reseeded separately and only referenced, never referencing.
DEMO_TABLES_CHILD_FIRST = [
    PlanEventOverride,                 # → seasonal_plan_entry, task (lost on reseed in the demo)
    Task,                              # → crop, field, user
    Alert, Notification,               # → user
    ChatMessage, Conversation,         # → conversation, user
    DashboardSummary, TaskIntelligenceSummary,   # → user
    WeeklyPlanEntry, WeeklyPlan,       # → weekly_plan, user
    SeasonalPlanEntry, SeasonalPlan,   # → seasonal_plan, user
    Crop,                              # → field, user
    Field,                             # → user
    User,
    Weather, WeatherForecast,
]


def clear_demo_tables():
    """Empty all demo tables. On Postgres, TRUNCATE ... RESTART IDENTITY also resets the
    id sequences, so seeded ids start at 1 again (as they do on SQLite after a full delete);
    the seeders and the demo rely on user 1. No CASCADE: if another table still referenced
    these, Postgres raises instead of silently emptying it."""
    if db.engine.dialect.name == "postgresql":
        quote = db.engine.dialect.identifier_preparer.quote
        tables = ", ".join(quote(m.__tablename__) for m in DEMO_TABLES_CHILD_FIRST)
        db.session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY"))
    else:
        for model in DEMO_TABLES_CHILD_FIRST:
            model.query.delete()
    db.session.commit()


def run():
    # DO NOT create app here (run.py already did it)

    clear_demo_tables()

    # ---- USERS ----
    user = [
        User(name="Ahmad Khan",    location="Punjab, Pakistan"),
        User(name="Ali Raza",      location="Sindh, Pakistan"),
        User(name="Faisal Mehmood",location="Islamabad Capital Territory, Pakistan"),
    ]

    db.session.add_all(user)
    db.session.commit()

    # ---- FIELDS ----
    # soil_type_id: 1=Sandy  2=Loamy  3=Clay
    # water_source_id: 1=Canal/River  2=Groundwater  3=Recycled
    
    sample_fields = [
        Field(                                      # 0 – North Field Alpha
            name="North Field Alpha",
            user_id=user[0].id,
            acreage=12.5,
            health_status="healthy",
            field_score=92.0,
            health_percentage=90.0,
            moisture_level=55.0,  # 55% → band "30-60"; keeps soil_moisture ">60" rule silent
            heat_level=28.0,
            stress_risk=10.0,
            disease_risk="low",
            water_source_id=2,
            soil_type_id=1,
            location="Punjab, Pakistan",
            ph_level=6.8,
            currently_active=True,
        ),
        Field(                                      # 1 – The Reservoir
            name="The Reservoir",
            user_id=user[0].id,
            acreage=5.5,
            health_status="healthy",
            field_score=95.0,
            health_percentage=82.0,
            moisture_level=55.0,  # 55% → band "30-60"; >60 would block Cotton sowing every day
            heat_level=30.0,
            stress_risk=8.0,
            disease_risk="high",
            water_source_id=3,
            soil_type_id=2,
            location="Punjab, Pakistan",
            ph_level=6.9,
            currently_active=True,
        ),
        Field(                                      # 2 – Punjab Wheat Belt
            name="Punjab Wheat Belt",
            user_id=user[0].id,
            acreage=50.0,
            health_status="alert",
            field_score=72.0,
            health_percentage=75.0,
            moisture_level=55.0,
            heat_level=32.0,
            stress_risk=28.0,
            disease_risk="medium",
            water_source_id=2,
            soil_type_id=2,
            location="Punjab, Pakistan",
            ph_level=7.0,
            currently_active=True,   # Maize's field in user 1's active seasonal plan
        ),
        Field(                                      # 3 – KP Highland Terrace
            name="KP Highland Terrace",
            user_id=user[1].id,
            acreage=9.3,
            health_status="alert",
            field_score=70.0,
            health_percentage=72.0,
            moisture_level=50.0,
            heat_level=22.0,
            stress_risk=30.0,
            disease_risk="medium",
            water_source_id=2,
            soil_type_id=1,
            location="Sindh, Pakistan",
            ph_level=6.5,
            currently_active=True,
        ),
        Field(                                      # 4 – Lower Indus Plain
            name="Lower Indus Plain",
            user_id=user[1].id,
            acreage=60.0,
            health_status="critical",
            field_score=58.0,
            health_percentage=60.0,
            moisture_level=42.0,
            heat_level=38.0,
            stress_risk=45.0,
            disease_risk="high",
            water_source_id=1,
            soil_type_id=3,
            location="Sindh, Pakistan",
            ph_level=7.8,
            currently_active=False,
        ),
        Field(                                      # 5 – Margalla Foothills Plot
            name="Margalla Foothills Plot",
            user_id=user[2].id,
            acreage=14.7,
            health_status="critical",
            field_score=61.0,
            health_percentage=68.0,
            moisture_level=38.0,
            heat_level=40.0,
            stress_risk=12.0,
            disease_risk="medium",
            water_source_id=2,
            soil_type_id=2,
            location="Islamabad Capital Territory, Pakistan",
            ph_level=6.7,
            currently_active=True,
        ),
    ]

    db.session.add_all(sample_fields)
    db.session.commit()

    # ---- CROPS ----
    # crop_name_id: 1=Maize(120d), 2=Rice(180d), 3=Cotton(220d)
    today = clock.today()

    def harvest(name_id, planted):
        durations = {1: 120, 2: 180, 3: 220}
        return planted + timedelta(days=durations.get(name_id, 150))

    sample_crops = [
        Crop(                                       # 0 – Rice in North Field Alpha
            crop_name_id=2, currently_active=True,
            current_growth_stage_id=3,
            current_health_status="alert",
            planting_date=today - timedelta(days=120),
            expected_harvest_date=harvest(2, today - timedelta(days=120)),
            currently_water_requirement=450.0,
            field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        Crop(                                       # 1 – Cotton in The Reservoir
            crop_name_id=3, currently_active=True,
            current_growth_stage_id=3,
            current_health_status="alert",
            planting_date=today - timedelta(days=90),
            expected_harvest_date=harvest(3, today - timedelta(days=90)),
            currently_water_requirement=750.0,
            field_id=sample_fields[1].id, user_id=user[0].id,
        ),
        Crop(                                       # 2 – Maize in Punjab Wheat Belt
            crop_name_id=1, currently_active=True,
            current_growth_stage_id=2,
            current_health_status="critical",
            planting_date=today - timedelta(days=30),
            expected_harvest_date=harvest(1, today - timedelta(days=30)),
            currently_water_requirement=600.0,
            field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        Crop(                                       # 3 – Rice in KP Highland Terrace
            crop_name_id=2, currently_active=False,
            current_growth_stage_id=1,
            current_health_status="healthy",
            planting_date=today - timedelta(days=10),
            expected_harvest_date=harvest(2, today - timedelta(days=10)),
            currently_water_requirement=1000.0,
            field_id=sample_fields[3].id, user_id=user[1].id,
        ),
        Crop(                                       # 4 – Cotton in Lower Indus Plain
            crop_name_id=3, currently_active=True,
            current_growth_stage_id=2,
            current_health_status="healthy",
            planting_date=today - timedelta(days=60),
            expected_harvest_date=harvest(3, today - timedelta(days=60)),
            currently_water_requirement=800.0,
            field_id=sample_fields[4].id, user_id=user[1].id,
        ),
        Crop(                                       # 5 – Maize in Margalla Foothills Plot
            crop_name_id=1, currently_active=True,
            current_growth_stage_id=1,
            current_health_status="critical",
            planting_date=today - timedelta(days=15),
            expected_harvest_date=harvest(1, today - timedelta(days=15)),
            currently_water_requirement=500.0,
            field_id=sample_fields[5].id, user_id=user[2].id,
        ),
    ]

    db.session.add_all(sample_crops)
    db.session.commit()

    # ---- TASKS ----
    # 15 total tasks: 8 for user[0] (Ahmad Khan), 4 for user[1] (Ali Raza), 3 for user[2] (Faisal Mehmood)
    # Tasks properly aligned with crops, fields, and users
    sample_tasks = [
        # ── User[0] - Ahmad Khan (Punjab) — 8 tasks ───────────────────────────────────
        # Task 1: Sow Rice in North Field Alpha (crop_id=sample_crops[0])
        Task(
            title="Sow Rice — North Field Alpha",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="planting", task_category="crop",
            description="Sow rice at North Field Alpha per weekly plan. Baseline conditions (25°C, 50-100mm) are within acceptable range.",
            notes="Weekly plan event: sowing 2026-05-18.",
            crop_id=sample_crops[0].id, field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        # Task 2: Irrigate Rice in North Field Alpha (crop_id=sample_crops[0])
        Task(
            title="Irrigate Rice — North Field Alpha",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today + timedelta(days=3),
            task_type="irrigation", task_category="crop",
            description="First irrigation for rice — 3 days post-sowing per rulebook (irrigation_calendar: days_after_sowing=3).",
            notes="Weekly plan event: irrigation 2026-05-21.",
            crop_id=sample_crops[0].id, field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        # Task 3: Fertilize Maize in Punjab Wheat Belt (crop_id=sample_crops[2])
        Task(
            title="Fertilize Maize — Punjab Wheat Belt",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today + timedelta(days=2),
            task_type="fertilizing", task_category="field",
            description="Increase fertilization for maize sowing — 50-100mm rainfall band is below rainfed threshold; supplemental nutrients critical at germination.",
            notes="Weekly plan adjustment: Maize Sowing + rainfall 50-100mm → fertilization increase (minimal).",
            crop_id=sample_crops[2].id, field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        # Task 4: Spray Fungicide on Cotton in The Reservoir (crop_id=sample_crops[1])
        Task(
            title="Spray Fungicide — The Reservoir Cotton",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="spraying", task_category="crop",
            description="Apply preventive fungicide to flowering cotton. Humidity band 40-70% with moisture risk warrants treatment.",
            notes="Cotton at flowering stage — inspect boll development during application.",
            crop_id=sample_crops[1].id, field_id=sample_fields[1].id, user_id=user[0].id,
        ),
        # Task 5: Irrigate Crops Morning Round in North Field Alpha (field_id=sample_fields[0])
        Task(
            title="Irrigate Crops — Morning Round",
            priority="low", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="irrigation", task_category="general",
            description="Irrigate crops during the morning hours to minimize evaporation.",
            notes="Ensure even water distribution across all fields.",
            crop_id=None, field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        # Task 6: Emergency Field Inspection in Punjab Wheat Belt (field_id=sample_fields[2])
        Task(
            title="Emergency Field Inspection — Punjab Wheat Belt",
            priority="critical", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="inspection", task_category="general",
            description="Urgent inspection of Punjab Wheat Belt for signs of crop stress, disease, and soil damage.",
            notes="Check leaf colour, soil surface, and drainage channels. Report findings immediately.",
            crop_id=None, field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        # Task 7: Repair Broken Irrigation Pipe in North Field Alpha (field_id=sample_fields[0])
        Task(
            title="Repair Broken Irrigation Pipe",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            description="Fix the damaged irrigation pipe in the North Field to restore water supply.",	
            notes="Assess damage and replace pipe section as needed.",
            task_type="maintenance", task_category="general",
            crop_id=None, field_id=sample_fields[0].id, user_id=user[0].id,	
        ),
        # Task 8: Address Soil Erosion in The Reservoir (field_id=sample_fields[1])
        Task(
            title="Address Soil Erosion in The Reservoir",
            priority="critical", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            description="Implement erosion control measures in The Reservoir field to prevent further soil loss.",
            notes="Consider terracing or cover cropping to stabilize soil.",
            task_type="soil_conservation", task_category="field",
            crop_id=None, field_id=sample_fields[1].id, user_id=user[0].id,
        ),
        Task(
            title="Drain excess moisture from North Field Apha",
            priority="critical", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            description="Implement erosion control measures in The Reservoir field to prevent further soil loss.",
            notes="Consider add drainage pipe or some chemicals to stabilize soil moisture.",
            task_type="drainage", task_category="field",
            crop_id=None, field_id=sample_fields[0].id, user_id=user[0].id,
        ),

        # ── User[1] - Ali Raza (Sindh) — 4 tasks ──────────────────────────────────────
        # Task 9: Irrigate Maize in KP Highland Terrace (crop_id=sample_crops[3])
        Task(
            title="Monitor Rice — KP Highland Terrace",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="monitoring", task_category="crop",
            description="Monitor seedling rice crop for early growth indicators and disease signs.",
            notes="Early-stage rice is sensitive to environmental changes; regular inspection advised.",
            crop_id=sample_crops[3].id, field_id=sample_fields[3].id, user_id=user[1].id,
        ),
        # Task 10: Spray Pesticide in Lower Indus Plain (crop_id=sample_crops[4])
        Task(
            title="Spray Pesticide — Lower Indus Plain Cotton",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="spraying", task_category="crop",
            description="Preventive pesticide application. Hot dry conditions increase pest pressure.",
            notes="Unaffected by irrigation action directly — priority will drop -1 level (medium→low).",
            crop_id=sample_crops[4].id, field_id=sample_fields[4].id, user_id=user[1].id,
        ),
        # Task 11: Fertilize Cotton in Lower Indus Plain (crop_id=sample_crops[4])
        Task(
            title="Fertilize Cotton — Lower Indus Plain",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=today + timedelta(days=1),
            task_type="fertilizing", task_category="field",
            description="Apply balanced fertilizer to cotton at vegetative stage to support canopy development.",
            notes="Ensure nutrient application before flowering stage begins.",
            crop_id=sample_crops[4].id, field_id=sample_fields[4].id, user_id=user[1].id,
        ),
        # Task 12: Irrigate Rice in KP Highland Terrace (crop_id=sample_crops[3])
        Task(
            title="Irrigate Rice — KP Highland Terrace",
            priority="low", completed=False,
            created_at=datetime.utcnow(), due_date=today + timedelta(days=1),
            task_type="irrigation", task_category="crop",
            description="Scheduled irrigation for seedling rice crop. Monitor soil moisture and adjust frequency as needed.",
            notes="Seedling stage rice requires consistent moisture without waterlogging.",
            crop_id=sample_crops[3].id, field_id=sample_fields[3].id, user_id=user[1].id,
        ),

        # ── User[2] - Faisal Mehmood (Islamabad) — 3 tasks ────────────────────────────
        # Task 13: Irrigate Maize in Margalla Foothills Plot (crop_id=sample_crops[5])
        Task(
            title="Irrigate Maize — Margalla Foothills Plot",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=today,
            task_type="irrigation", task_category="crop",
            description="Scheduled maize irrigation. Heatwave forecast with zero rainfall — critical irrigation frequency increase required.",
            notes="IMPACT_TASKS expected: irrigation.increase days.significant → priority critical, task delayed.",
            crop_id=sample_crops[5].id, field_id=sample_fields[5].id, user_id=user[2].id,
        ),
        # Task 14: Apply Mulch in Margalla Foothills Plot (field_id=sample_fields[5])
        Task(
            title="Apply Mulch — Margalla Foothills Plot",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today - timedelta(days=1),
            task_type="mulching", task_category="field",
            description="Apply organic mulch to maize field to retain soil moisture and regulate temperature.",
            notes="Mulching essential during heatwave period to prevent crop stress.",
            crop_id=None, field_id=sample_fields[5].id, user_id=user[2].id,
        ),
        # Task 15: Check Soil pH in Margalla Foothills Plot (field_id=sample_fields[5])
        Task(
            title="Check Soil pH — Margalla Foothills Plot",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=today + timedelta(days=2),
            task_type="soil_testing", task_category="field",
            description="Test soil pH level to ensure optimal nutrient availability for maize crop.",
            notes="Target pH 6.5-7.0 for maize; adjust if needed.",
            crop_id=None, field_id=sample_fields[5].id, user_id=user[2].id,
        ),
    ]

    db.session.add_all(sample_tasks)
    db.session.commit()

    # # ---- ALERTS ----
    # sample_alert = [
    #     Alert(user_id=user[0].id, crop_id=sample_crops[0].id, level="medium",
    #           message="Rice crop requires irrigation support during vegetative stage."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[1].id, level="high",
    #           message="High humidity increases fungal risk for flowering cotton."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[2].id, level="high",
    #           message="Drainage issues may worsen maize crop stress."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[3].id, level="low",
    #           message="Routine equipment check recommended near reservoir seedling field."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[4].id, level="high",
    #           message="Crop in flowering stage requires inspection due to strong winds."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[5].id, level="medium",
    #           message="Vegetative cotton crop would benefit from timely fertilization."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[6].id, level="medium",
    #           message="Seedling-stage may be vulnerable to low temperatures in highland area."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[7].id, level="high",
    #           message="Flowering rice crop is under high environmental stress in Lower Indus Plain."),
    #     Alert(user_id=user[0].id, crop_id=sample_crops[8].id, level="low",
    #           message="Maize crop is stable but should continue routine monitoring."),
    # ]

    # db.session.add_all(sample_alert)
    # db.session.commit()

    # ---- NOTIFICATIONS ----
    sample_notifications = [
    #     Notification(user_id=user[0].id, title="Irrigation recommended for rice",
    #                  message="Your rice crop in North Field Alpha needs irrigation during the vegetative stage.",
    #                  detail="Adequate irrigation at this stage helps ensure strong tiller development and prevents early stress.",
    #                  notification_type="recommendation", is_read=False, created_at=datetime.utcnow()),
    #     Notification(user_id=user[0].id, title="Fungal risk warning for cotton",
    #                  message="High humidity conditions increase fungal risk in your East Creek Basin field.",
    #                  detail="Flowering cotton is especially sensitive to prolonged moisture. Preventive spraying can reduce future losses.",
    #                  notification_type="warning", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Drainage issue detected",
                     message="Water drainage problems may impact maize health at South Hill Slope.",
                     detail="Poor drainage can result in root stress and nutrient imbalance. Clearing channels is advised as soon as possible.",
                     notification_type="critical", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Routine equipment check",
                     message="This is a reminder to check irrigation and field equipment near the reservoir plot.",
                     detail=None, notification_type="info", is_read=False, created_at=datetime.utcnow()),
    #     Notification(user_id=user[0].id, title="Wheat flowering stage alert",
    #                  message="Your crop has entered the flowering stage and requires close monitoring.",
    #                  detail="Strong winds during flowering can affect yield. Regular inspection can help detect issues early.",
    #                  notification_type="warning", is_read=False, created_at=datetime.utcnow()),
    #     Notification(user_id=user[0].id, title="Fertilization recommended for cotton",
    #                  message="Cotton at the vegetative stage may benefit from balanced fertilization.",
    #                  detail="Timely nutrient application supports healthy canopy development and prepares the crop for flowering.",
    #                  notification_type="recommendation", is_read=False, created_at=datetime.utcnow()),
    #     Notification(user_id=user[0].id, title="Cold stress risk for wheat seedlings",
    #                  message="Seedlings may experience stress due to dropping night temperatures.",
    #                  detail="Early-stage wheat is sensitive to cold spells. Monitoring weather forecasts is strongly advised.",
    #                  notification_type="warning", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="High stress alert for rice crop",
                     message="Your rice crop is experiencing high environmental stress during flowering.",
                     detail="Combined heat and nutrient stress at this stage can significantly reduce yield. Immediate attention is required.",
                     notification_type="critical", is_read=False, created_at=datetime.utcnow()),
    #     Notification(user_id=user[0].id, title="Maize crop status update",
    #                  message="Your maize crop is healthy and progressing well in the vegetative stage.",
    #                  detail=None, notification_type="info", is_read=False, created_at=datetime.utcnow()),
    ]

    db.session.add_all(sample_notifications)
    db.session.commit()

    seed_demo_weather(start=clock.today())

    print("Sample data seeded successfully.")
    print(f"Users:        {User.query.count()}")
    print(f"Crops:        {Crop.query.count()}")
    print(f"Fields:       {Field.query.count()}")
    print(f"Tasks:        {Task.query.count()}")
    print(f"Weather rows: {Weather.query.count()}")


def seed_demo_weather(start: date) -> None:
    """Insert 7 days of baseline weather and harsh forecasts, starting at `start`.

    Demo weather is always relative to the given start date (normally today), so
    the Weather Change Simulator finds data on any day. Existing rows in the
    7-day window are replaced to avoid duplicates.
    """
    end = start + timedelta(days=6)
    Weather.query.filter(Weather.date >= start, Weather.date <= end).delete()
    WeatherForecast.query.filter(
        WeatherForecast.date >= start, WeatherForecast.date <= end
    ).delete()
    db.session.commit()

    # ---- WEATHER (historical baseline) ----
    # Weather is keyed by user location (one region per user).
    # user[0] Ahmad Khan → "Punjab, Pakistan" — primary test user for weekly plan & risk assessment.
    #
    # Punjab = early May (Kharif sowing season; run the demo with DEMO_TODAY=2027-05-05).
    # Typical early-May values for central Punjab: daily mean 31–33 °C, humidity 25–35 %,
    # no rain, 10–10.5 h of sunshine. Bands: temperature 30–40, humidity <40,
    # rainfall <50 (daily mm), sunlight >8. Rule outcomes (Sowing stage):
    #   Maize  → sowing suitable (only 15–20 °C or soil moisture >60 % block it);
    #            dry days add irrigation (rainfall <50, humidity <40)
    #   Cotton → sowing suitable (needs 30–40 °C, sunlight >8 h, humidity ≤70 %)
    #   Rice   → Not Feasible on Sandy soil (skipped); 30–40 °C would also delay its sowing
    # Field moisture for North Field Alpha set to 55% so soil_moisture ">60" does not fire.

    NORMAL_REGIONS = {
        "Punjab, Pakistan": [
            # (avg_temp, humidity, rainfall_mm, sunlight_h, wind_kph, notes)
            (31.5, 32, 0.0, 10.2, 11, "Hot and dry; clear skies."),
            (32.0, 30, 0.0, 10.4, 12, "Hot and sunny; typical early May."),
            (32.5, 29, 0.0, 10.5, 13, "Clear; afternoon heat around 39 °C."),
            (32.0, 31, 0.0, 10.3, 12, "Dry and sunny."),
            (32.8, 28, 0.0, 10.5, 14, "Hot, dry westerly breeze."),
            (33.0, 27, 0.0, 10.6, 12, "Clear and hot."),
            (32.5, 30, 0.0, 10.4, 11, "Hot and sunny; no rain expected."),
        ],
        "Sindh, Pakistan": [
            # ~32°C → band "30-40" → Rice Sowing: sowing.delay.minimal + irrigation.increase quantity (ignored)
            (32.0, 52, 60.0, 10.0, 16, "Warm day above 30°C; delay rice sowing by 4 days."),
            (31.5, 54, 55.0,  9.8, 15, "Sustained warmth; irrigation well managed."),
            (32.5, 50, 62.0, 10.5, 17, "Hot; monitor soil temperature before sowing."),
            (31.8, 53, 58.0, 10.2, 16, "Warm and humid; rice pre-sowing conditions."),
            (32.2, 52, 60.0,  9.5, 14, "Above 30°C threshold; sowing delayed as precaution."),
            (31.5, 55, 57.0,  9.8, 15, "Moderate warmth with adequate rainfall."),
            (32.0, 51, 61.0, 10.0, 16, "Typical warm Sindh May; conditions stabilising."),
        ],
        "Khyber Pakhtunkhwa, Pakistan": [
            # "20-30" temp + "50-100" rainfall → no rules fire
            (21.0, 60, 55.0, 7.5, 10, "Mild highland conditions; no adjustments needed."),
            (21.5, 58, 60.0, 8.0,  9, "Clear morning; adequate rainfall."),
            (20.5, 63, 58.0, 7.0, 11, "Moderate moisture; within safe bands."),
            (22.0, 57, 55.0, 8.5, 10, "Sunny intervals; normal for the season."),
            (22.5, 55, 62.0, 9.0, 12, "Comfortable; optimal conditions."),
            (21.0, 62, 57.0, 7.2,  9, "Light showers; soil moist but not waterlogged."),
            (21.0, 64, 60.0, 7.0,  8, "Overcast morning; afternoon clearing."),
        ],
        "Islamabad Capital Territory, Pakistan": [
            # "20-30" temp + "50-100" rainfall → no rules fire
            (26.0, 56, 58.0, 8.5, 13, "Pleasant spring day; good field conditions."),
            (26.5, 54, 55.0, 9.0, 14, "Mostly clear; moderate temperature."),
            (25.5, 60, 62.0, 7.5, 12, "Light showers; soil moisture replenished."),
            (26.0, 58, 57.0, 8.0, 13, "Patchy cloud; comfortable for field work."),
            (27.0, 52, 60.0, 9.0, 15, "Warm and sunny; no stress conditions."),
            (27.5, 50, 55.0, 9.5, 14, "Clear skies; ideal conditions."),
            (26.2, 57, 58.0, 8.2, 13, "Light evening shower possible."),
        ],
    }

    weather_rows = []
    for region, days in NORMAL_REGIONS.items():
        for offset, (temp, hum, rain, sun, wind, note) in enumerate(days):
            weather_rows.append(Weather(
                region=region,
                date=start + timedelta(days=offset),
                avg_temperature_c=temp,
                humidity=hum,
                rainfall_mm=rain,
                sunlight_hours=sun,
                wind_speed_kph=wind,
                notes=note,
                created_at=datetime.utcnow(),
            ))

    db.session.add_all(weather_rows)
    db.session.commit()

    # ---- WEATHER FORECAST (harsh/extreme conditions — for risk & change detection) ----
    # Compared against the weather baseline above to assess climate risk and trigger alerts.
    # Punjab: early-May western disturbance (days 3–4). Sindh: extreme heat. KP: flood risk. Islamabad: heatwave.

    HARSH_FORECAST_REGIONS = {
        "Punjab, Pakistan": [
            # Same as the baseline, except a western disturbance on days 3–4 (common in
            # early May): dust storm and thundershowers, cooler and cloudy. Bands change to
            # temperature 20–30, humidity 40–70, sunlight 4–8 → IMPACT_PLAN; Cotton's sowing
            # rules reject both days (temperature 20–30 °C, sunlight 4–8 h).
            (31.8, 31, 0.0, 10.2, 12, "Hot and dry; as expected."),
            (32.2, 30, 0.0, 10.3, 13, "Hot and sunny; as expected."),
            (27.5, 58, 8.0,  5.5, 38, "Western disturbance: dust storm, then thundershowers."),
            (28.0, 55, 4.0,  6.0, 24, "Unsettled; scattered showers and cloud."),
            (32.5, 33, 0.0, 10.2, 14, "Clearing; hot and sunny again."),
            (33.2, 28, 0.0, 10.5, 12, "Hot and dry."),
            (33.5, 27, 0.0, 10.6, 11, "Hot and dry."),
        ],
        "Sindh, Pakistan": [
            # Extreme heat — well above 38°C, severe desiccation and crop failure risk
            (41.5, 28, 0.0, 12.0, 28, "Extreme heat event; crop desiccation risk is critical."),
            (42.0, 25, 0.0, 12.5, 30, "Heatwave peak; suspend all field operations midday."),
            (40.8, 27, 0.0, 12.0, 27, "Drought conditions worsening; double irrigation frequency."),
            (42.5, 24, 0.0, 12.5, 31, "Record high; rice flowering severely threatened."),
            (41.0, 26, 0.0, 12.0, 29, "No rainfall forecast; soil moisture depleting rapidly."),
            (43.0, 23, 0.0, 12.5, 32, "Highest temperature of season; immediate shade required."),
            (41.8, 25, 0.0, 12.0, 28, "Sustained extreme heat; crop loss risk without intervention."),
        ],
        "Khyber Pakhtunkhwa, Pakistan": [
            # Flash flood risk — extreme rainfall and low sunlight
            (16.0, 90, 38.0, 2.0,  8, "Flash flood warning issued; evacuate low-lying fields."),
            (15.5, 92, 42.0, 1.5,  7, "Heaviest rainfall of the year; field access impossible."),
            (16.5, 88, 35.0, 2.5,  9, "Rivers at high levels; waterlogging extensive."),
            (15.8, 91, 40.0, 2.0,  8, "Landslide risk in slope fields; suspend all operations."),
            (17.0, 87, 28.0, 3.0, 10, "Rain easing slightly but soil saturated."),
            (16.2, 93, 45.0, 1.0,  6, "Record 24-hour rainfall; crop damage expected."),
            (15.5, 90, 36.0, 2.0,  7, "Persistent flooding; assess damage before resuming work."),
        ],
        "Islamabad Capital Territory, Pakistan": [
            # Heatwave — temperatures 36-40°C with dry conditions
            (37.0, 32, 0.0, 11.5, 22, "Heatwave advisory; avoid outdoor work 11am–4pm."),
            (38.5, 28, 0.0, 12.0, 24, "Dangerously hot; irrigate twice daily to prevent crop loss."),
            (36.8, 30, 0.0, 11.5, 23, "Third consecutive heatwave day; heat stress accumulating."),
            (39.0, 27, 0.0, 12.0, 25, "Peak heatwave; soil surface temperature exceeds 50°C."),
            (37.5, 29, 0.0, 11.5, 22, "No relief forecast; maintain emergency irrigation."),
            (40.0, 25, 0.0, 12.0, 26, "Hottest day on record for May; critical intervention needed."),
            (38.0, 28, 0.0, 12.0, 24, "Heatwave persists; crop stress and wilting observed."),
        ],
    }

    weather_forecast_rows = []
    for region, days in HARSH_FORECAST_REGIONS.items():
        for offset, (temp, hum, rain, sun, wind, note) in enumerate(days):
            weather_forecast_rows.append(WeatherForecast(
                region=region,
                date=start + timedelta(days=offset),
                avg_temperature_c=temp,
                humidity=hum,
                rainfall_mm=rain,
                sunlight_hours=sun,
                wind_speed_kph=wind,
                notes=note,
                created_at=datetime.utcnow(),
            ))

    db.session.add_all(weather_forecast_rows)
    db.session.commit()
