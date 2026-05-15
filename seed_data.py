from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.models.crop import Crop
from app.models.field import Field
from app.models.task import Task
from app.models.alert import Alert
from app.models.weather import ClimateProfile
from app.models.weather_forecast import CurrentWeatherProfile


def run():
    # DO NOT create app here (run.py already did it)

    # Clear in correct dependency order
    Task.query.delete()
    Alert.query.delete()
    Notification.query.delete()
    Crop.query.delete()
    Field.query.delete()
    User.query.delete()
    ClimateProfile.query.delete()
    CurrentWeatherProfile.query.delete()
    db.session.commit()

    # ---- USERS ----
    user = [
        User(name="Ahmad Khan",    location="Punjab, Pakistan"),
        User(name="Ali Raza",      location="Sindh, Pakistan"),
        User(name="Muhammad Usman",location="Khyber Pakhtunkhwa, Pakistan"),
        User(name="Bilal Ahmed",   location="Punjab, Pakistan"),
        User(name="Hassan Qureshi",location="Punjab, Pakistan"),
        User(name="Sajid Hussain", location="Sindh, Pakistan"),
        User(name="Imran Shah",    location="Khyber Pakhtunkhwa, Pakistan"),
        User(name="Naveed Akhtar", location="Sindh, Pakistan"),
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
            moisture_level=65.0,
            heat_level=28.0,
            stress_risk=10.0,
            disease_risk="low",
            water_source_id=2,
            soil_type_id=2,
            location="Punjab, Pakistan",
            ph_level=6.8,
            currently_active=True,
        ),
        Field(                                      # 1 – East Creek Basin
            name="East Creek Basin",
            user_id=user[0].id,
            acreage=34.2,
            health_status="alert",
            field_score=64.0,
            health_percentage=65.0,
            moisture_level=45.0,
            heat_level=25.0,
            stress_risk=35.0,
            disease_risk="medium",
            water_source_id=1,
            soil_type_id=3,
            location="Sindh, Pakistan",
            ph_level=7.2,
            currently_active=True,
        ),
        Field(                                      # 2 – South Hill Slope
            name="South Hill Slope",
            user_id=user[0].id,
            acreage=18.0,
            health_status="critical",
            field_score=88.0,
            health_percentage=88.0,
            moisture_level=60.0,
            heat_level=27.0,
            stress_risk=15.0,
            disease_risk="high",
            water_source_id=2,
            soil_type_id=1,
            location="Punjab, Pakistan",
            ph_level=6.2,
            currently_active=False,
        ),
        Field(                                      # 3 – The Reservoir
            name="The Reservoir",
            user_id=user[0].id,
            acreage=5.5,
            health_status="healthy",
            field_score=95.0,
            health_percentage=82.0,
            moisture_level=70.0,
            heat_level=30.0,
            stress_risk=8.0,
            disease_risk="high",
            water_source_id=3,
            soil_type_id=2,
            location="Punjab, Pakistan",
            ph_level=6.9,
            currently_active=False,
        ),
        Field(                                      # 4 – Punjab Wheat Belt
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
            currently_active=True,
        ),
        Field(                                      # 5 – Sindh Canal Edge
            name="Sindh Canal Edge",
            user_id=user[0].id,
            acreage=40.8,
            health_status="healthy",
            field_score=89.0,
            health_percentage=88.0,
            moisture_level=68.0,
            heat_level=34.0,
            stress_risk=12.0,
            disease_risk="low",
            water_source_id=1,
            soil_type_id=3,
            location="Sindh, Pakistan",
            ph_level=7.4,
            currently_active=True,
        ),
        Field(                                      # 6 – KP Highland Terrace
            name="KP Highland Terrace",
            user_id=user[0].id,
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
            location="Khyber Pakhtunkhwa, Pakistan",
            ph_level=6.5,
            currently_active=True,
        ),
        Field(                                      # 7 – Lower Indus Plain
            name="Lower Indus Plain",
            user_id=user[0].id,
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
            currently_active=True,
        ),
        Field(                                      # 8 – Margalla Foothills Plot
            name="Margalla Foothills Plot",
            user_id=user[0].id,
            acreage=14.7,
            health_status="healthy",
            field_score=91.0,
            health_percentage=89.0,
            moisture_level=66.0,
            heat_level=26.0,
            stress_risk=12.0,
            disease_risk="low",
            water_source_id=2,
            soil_type_id=2,
            location="Islamabad Capital Territory, Pakistan",
            ph_level=6.7,
            currently_active=False,
        ),
    ]

    db.session.add_all(sample_fields)
    db.session.commit()

    # ---- CROPS ----
    # crop_name_id: 1=Maize(120d), 2=Rice(180d), 3=Cotton(220d)
    today = date.today()

    def harvest(name_id, planted):
        durations = {1: 120, 2: 180, 3: 220}
        return planted + timedelta(days=durations.get(name_id, 150))

    sample_crops = [
        Crop(                                       # Rice – 45 days in (25%)
            crop_name_id=2, currently_active=True,
            current_growth_stage_id=2,
            current_health_status="healthy",
            planting_date=today - timedelta(days=45),
            expected_harvest_date=harvest(2, today - timedelta(days=45)),
            currently_water_requirement=900.0,
            field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        Crop(                                       # Cotton – 90 days in (41%)
            crop_name_id=3, currently_active=True,
            current_growth_stage_id=3,
            current_health_status="alert",
            planting_date=today - timedelta(days=90),
            expected_harvest_date=harvest(3, today - timedelta(days=90)),
            currently_water_requirement=750.0,
            field_id=sample_fields[1].id, user_id=user[0].id,
        ),
        Crop(                                       # Maize – 30 days in (25%)
            crop_name_id=1, currently_active=False,
            current_growth_stage_id=2,
            current_health_status="critical",
            planting_date=today - timedelta(days=30),
            expected_harvest_date=harvest(1, today - timedelta(days=30)),
            currently_water_requirement=600.0,
            field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        Crop(                                       # Rice – 10 days in (6%)
            crop_name_id=2, currently_active=False,
            current_growth_stage_id=1,
            current_health_status="healthy",
            planting_date=today - timedelta(days=10),
            expected_harvest_date=harvest(2, today - timedelta(days=10)),
            currently_water_requirement=1000.0,
            field_id=sample_fields[3].id, user_id=user[0].id,
        ),
        Crop(                                       # Rice – 120 days in (67%)
            crop_name_id=2, currently_active=True,
            current_growth_stage_id=3,
            current_health_status="alert",
            planting_date=today - timedelta(days=120),
            expected_harvest_date=harvest(2, today - timedelta(days=120)),
            currently_water_requirement=450.0,
            field_id=sample_fields[4].id, user_id=user[0].id,
        ),
        Crop(                                       # Cotton – 60 days in (27%)
            crop_name_id=3, currently_active=True,
            current_growth_stage_id=2,
            current_health_status="healthy",
            planting_date=today - timedelta(days=60),
            expected_harvest_date=harvest(3, today - timedelta(days=60)),
            currently_water_requirement=800.0,
            field_id=sample_fields[5].id, user_id=user[0].id,
        ),
        Crop(                                       # Maize – 15 days in (13%)
            crop_name_id=1, currently_active=True,
            current_growth_stage_id=1,
            current_health_status="alert",
            planting_date=today - timedelta(days=15),
            expected_harvest_date=harvest(1, today - timedelta(days=15)),
            currently_water_requirement=400.0,
            field_id=sample_fields[6].id, user_id=user[0].id,
        ),
        Crop(                                       # Rice – 160 days in (89%)
            crop_name_id=2, currently_active=True,
            current_growth_stage_id=3,
            current_health_status="critical",
            planting_date=today - timedelta(days=160),
            expected_harvest_date=harvest(2, today - timedelta(days=160)),
            currently_water_requirement=1100.0,
            field_id=sample_fields[7].id, user_id=user[0].id,
        ),
        Crop(                                       # Maize – 75 days in (63%)
            crop_name_id=1, currently_active=False,
            current_growth_stage_id=2,
            current_health_status="healthy",
            planting_date=today - timedelta(days=75),
            expected_harvest_date=harvest(1, today - timedelta(days=75)),
            currently_water_requirement=550.0,
            field_id=sample_fields[8].id, user_id=user[0].id,
        ),
    ]

    db.session.add_all(sample_crops)
    db.session.commit()

    # ---- TASKS ----
    sample_tasks = [
        # ── CROP tasks ──────────────────────────────────────────────────────
        Task(
            title="Irrigate Rice",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="irrigation", task_category="crop",
            description="Provide controlled irrigation to support vegetative rice growth.",
            notes="Soil moisture currently stable.",
            crop_id=sample_crops[0].id, field_id=sample_fields[0].id, user_id=user[0].id,
        ),
        Task(
            title="Spray Fungicide on Cotton",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="spraying", task_category="crop",
            description="Apply preventive fungicide to cotton during flowering to reduce disease risk.",
            notes="High humidity reported recently.",
            crop_id=sample_crops[1].id, field_id=sample_fields[1].id, user_id=user[0].id,
        ),
        Task(
            title="Harvest Maize",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=5),
            task_type="harvesting", task_category="crop",
            description="Begin maize harvest — crop has reached maturity.",
            notes="Ensure harvester is serviced beforehand.",
            crop_id=sample_crops[2].id, field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        Task(
            title="Prune Cotton Plants",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=3),
            task_type="pruning", task_category="crop",
            description="Remove excess lateral shoots to improve airflow and boll development.",
            notes="Focus on dense canopy areas.",
            crop_id=sample_crops[5].id, field_id=sample_fields[5].id, user_id=user[0].id,
        ),
        Task(
            title="Assist Rice Pollination",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=2),
            task_type="pollination", task_category="crop",
            description="Support pollination during heading stage by gentle agitation of rows.",
            notes="Schedule during morning hours for best results.",
            crop_id=sample_crops[4].id, field_id=sample_fields[4].id, user_id=user[0].id,
        ),
        Task(
            title="Defoliate Cotton Pre-Harvest",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=7),
            task_type="defoliation", task_category="crop",
            description="Apply defoliant to cotton to accelerate leaf drop before mechanical harvest.",
            notes="Check boll opening percentage before applying.",
            crop_id=sample_crops[1].id, field_id=sample_fields[1].id, user_id=user[0].id,
        ),

        # ── FIELD tasks ─────────────────────────────────────────────────────
        Task(
            title="Fertilize Lower Indus Soil",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="fertilizing", task_category="field",
            description="Apply balanced NPK fertilizer to restore soil nutrients.",
            notes="Canal water supply is adequate.",
            crop_id=None, field_id=sample_fields[5].id, user_id=user[0].id,
        ),
        Task(
            title="Soil pH Testing",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="soil_testing", task_category="field",
            description="Conduct soil pH and nutrient testing across the flowering rice field.",
            notes="Previous nutrient imbalance suspected.",
            crop_id=None, field_id=sample_fields[7].id, user_id=user[0].id,
        ),
        Task(
            title="Clear Drainage Channels",
            priority="high", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="drainage", task_category="field",
            description="Inspect and clear drainage channels to avoid water logging.",
            notes="Uneven slope requires attention.",
            crop_id=None, field_id=sample_fields[2].id, user_id=user[0].id,
        ),
        Task(
            title="Plow East Delta Field",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=4),
            task_type="plowing", task_category="field",
            description="Deep plow field to break compaction layer before next planting season.",
            notes="Use subsoil plow attachment.",
            crop_id=None, field_id=sample_fields[3].id, user_id=user[0].id,
        ),
        Task(
            title="Weed Control — Upper Punjab",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=2),
            task_type="weeding", task_category="field",
            description="Manual and chemical weeding around crop rows to reduce competition.",
            notes="Avoid herbicide drift near canal.",
            crop_id=None, field_id=sample_fields[6].id, user_id=user[0].id,
        ),
        Task(
            title="Prepare Sindh Plains for Planting",
            priority="low", completed=False,
            created_at=datetime.utcnow(), due_date=date.today() + timedelta(days=10),
            task_type="land_preparation", task_category="field",
            description="Level and prepare field bed for upcoming rice planting season.",
            notes="Laser leveling recommended.",
            crop_id=None, field_id=sample_fields[8].id, user_id=user[0].id,
        ),

        # ── GENERAL tasks ────────────────────────────────────────────────────
        Task(
            title="Routine Field Maintenance",
            priority="low", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="maintenance", task_category="general",
            description="General upkeep of farm infrastructure — fences, pathways, water points.",
            notes="Coordinate with field workers.",
            crop_id=None, field_id=None, user_id=user[0].id,
        ),
        Task(
            title="Farm Inspection Round",
            priority="medium", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="inspection", task_category="general",
            description="Full farm walkthrough to identify any unreported issues across all fields.",
            notes="Document findings in field log.",
            crop_id=None, field_id=None, user_id=user[0].id,
        ),
        Task(
            title="Equipment Check — Irrigation Pumps",
            priority="low", completed=False,
            created_at=datetime.utcnow(), due_date=date.today(),
            task_type="equipment_check", task_category="general",
            description="Inspect and service all irrigation pumps and sprayer units.",
            notes="Routine preventive maintenance before peak season.",
            crop_id=None, field_id=None, user_id=user[0].id,
        ),
    ]

    db.session.add_all(sample_tasks)
    db.session.commit()

    # ---- ALERTS ----
    sample_alert = [
        Alert(user_id=user[0].id, crop_id=sample_crops[0].id, level="medium",
              message="Rice crop requires irrigation support during vegetative stage."),
        Alert(user_id=user[0].id, crop_id=sample_crops[1].id, level="high",
              message="High humidity increases fungal risk for flowering cotton."),
        Alert(user_id=user[0].id, crop_id=sample_crops[2].id, level="high",
              message="Drainage issues may worsen maize crop stress."),
        Alert(user_id=user[0].id, crop_id=sample_crops[3].id, level="low",
              message="Routine equipment check recommended near reservoir seedling field."),
        Alert(user_id=user[0].id, crop_id=sample_crops[4].id, level="high",
              message="Crop in flowering stage requires inspection due to strong winds."),
        Alert(user_id=user[0].id, crop_id=sample_crops[5].id, level="medium",
              message="Vegetative cotton crop would benefit from timely fertilization."),
        Alert(user_id=user[0].id, crop_id=sample_crops[6].id, level="medium",
              message="Seedling-stage may be vulnerable to low temperatures in highland area."),
        Alert(user_id=user[0].id, crop_id=sample_crops[7].id, level="high",
              message="Flowering rice crop is under high environmental stress in Lower Indus Plain."),
        Alert(user_id=user[0].id, crop_id=sample_crops[8].id, level="low",
              message="Maize crop is stable but should continue routine monitoring."),
    ]

    db.session.add_all(sample_alert)
    db.session.commit()

    # ---- NOTIFICATIONS ----
    sample_notifications = [
        Notification(user_id=user[0].id, title="Irrigation recommended for rice",
                     message="Your rice crop in North Field Alpha needs irrigation during the vegetative stage.",
                     detail="Adequate irrigation at this stage helps ensure strong tiller development and prevents early stress.",
                     notification_type="recommendation", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Fungal risk warning for cotton",
                     message="High humidity conditions increase fungal risk in your East Creek Basin field.",
                     detail="Flowering cotton is especially sensitive to prolonged moisture. Preventive spraying can reduce future losses.",
                     notification_type="warning", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Drainage issue detected",
                     message="Water drainage problems may impact maize health at South Hill Slope.",
                     detail="Poor drainage can result in root stress and nutrient imbalance. Clearing channels is advised as soon as possible.",
                     notification_type="critical", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Routine equipment check",
                     message="This is a reminder to check irrigation and field equipment near the reservoir plot.",
                     detail=None, notification_type="info", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Wheat flowering stage alert",
                     message="Your crop has entered the flowering stage and requires close monitoring.",
                     detail="Strong winds during flowering can affect yield. Regular inspection can help detect issues early.",
                     notification_type="warning", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Fertilization recommended for cotton",
                     message="Cotton at the vegetative stage may benefit from balanced fertilization.",
                     detail="Timely nutrient application supports healthy canopy development and prepares the crop for flowering.",
                     notification_type="recommendation", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Cold stress risk for wheat seedlings",
                     message="Seedlings may experience stress due to dropping night temperatures.",
                     detail="Early-stage wheat is sensitive to cold spells. Monitoring weather forecasts is strongly advised.",
                     notification_type="warning", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="High stress alert for rice crop",
                     message="Your rice crop is experiencing high environmental stress during flowering.",
                     detail="Combined heat and nutrient stress at this stage can significantly reduce yield. Immediate attention is required.",
                     notification_type="critical", is_read=False, created_at=datetime.utcnow()),
        Notification(user_id=user[0].id, title="Maize crop status update",
                     message="Your maize crop is healthy and progressing well in the vegetative stage.",
                     detail=None, notification_type="info", is_read=False, created_at=datetime.utcnow()),
    ]

    db.session.add_all(sample_notifications)
    db.session.commit()

    # ---- DAILY WEATHER (ClimateProfile) ----
    # Seed 7 days starting today for 4 Pakistani regions.
    # Values reflect realistic May conditions in Pakistan.
    #
    # Punjab:    hot & dry (pre-monsoon)   ~30–34°C, low rain, high sun
    # Sindh:     very hot & dry            ~34–38°C, near-zero rain, high sun
    # KP:        cooler, occasional rain   ~22–26°C, moderate humidity
    # Islamabad: warm, intermittent shower ~26–30°C, moderate rain

    REGIONS = {
        "Punjab, Pakistan": [
            # (avg_temp, humidity, rainfall_mm, sunlight_h, wind_kph, notes)
            (31.2, 42, 0.0,  9.5, 14, "Clear hot day, pre-monsoon dryness."),
            (32.0, 40, 0.0,  9.8, 16, "Slight warming, no rain expected."),
            (31.5, 44, 2.0,  8.5, 18, "Patchy cloud, brief afternoon shower possible."),
            (30.8, 48, 5.5,  7.5, 20, "Light rain event; soil moisture improves."),
            (29.5, 52, 8.0,  6.5, 15, "Overcast morning, scattered showers."),
            (30.2, 50, 3.0,  8.0, 12, "Clearing by afternoon, moderate conditions."),
            (31.8, 45, 0.5,  9.2, 14, "Mostly sunny, warm and dry."),
        ],
        "Sindh, Pakistan": [
            (35.8, 35, 0.0, 10.5, 20, "Intense heat, no rainfall forecast."),
            (36.4, 33, 0.0, 10.8, 22, "Heatwave persisting; irrigation critical."),
            (36.0, 34, 0.0, 10.5, 21, "Continuous dry heat; monitor crop stress."),
            (35.2, 36, 0.0, 10.2, 19, "Slight humidity uptick but still very dry."),
            (34.8, 38, 1.5,  9.8, 17, "Trace rain; negligible soil moisture effect."),
            (35.5, 37, 0.0, 10.4, 20, "Hot and dry, irrigation schedule critical."),
            (36.2, 35, 0.0, 10.6, 22, "Peak heat; increase irrigation frequency."),
        ],
        "Khyber Pakhtunkhwa, Pakistan": [
            (24.0, 58, 4.5,  7.5, 12, "Mild day with intermittent cloud cover."),
            (23.5, 60, 6.0,  7.0, 10, "Cooler with moderate rain; good soil moisture."),
            (22.8, 62, 8.5,  6.5, 11, "Overcast with moderate showers."),
            (24.5, 55, 2.0,  8.0, 13, "Clearing after overnight rain."),
            (25.2, 52, 0.5,  8.5, 14, "Mostly sunny, mild breeze."),
            (23.0, 65, 12.0, 5.5, 9,  "Heavy shower; check field drainage."),
            (22.5, 68, 10.0, 5.0, 8,  "Wet and cool; delay spraying operations."),
        ],
        "Islamabad Capital Territory, Pakistan": [
            (28.5, 50, 3.0,  8.0, 15, "Warm with afternoon clouds."),
            (29.2, 48, 1.5,  8.5, 16, "Mostly clear, comfortable conditions."),
            (27.8, 55, 7.0,  7.0, 14, "Intermittent showers; soil moisture adequate."),
            (28.0, 54, 5.5,  7.5, 13, "Patchy rain; monitor drainage."),
            (29.5, 46, 0.5,  9.0, 17, "Clearing skies, warm afternoon."),
            (30.0, 44, 0.0,  9.5, 18, "Clear and warm, good sunlight hours."),
            (28.8, 52, 4.0,  7.8, 14, "Mild shower possible in evening."),
        ],
    }

    weather_rows = []
    for region, days in REGIONS.items():
        for offset, (temp, hum, rain, sun, wind, note) in enumerate(days):
            weather_rows.append(ClimateProfile(
                region=region,
                date=today + timedelta(days=offset),
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

    # ---- LEGACY WEATHER PROFILE (CurrentWeatherProfile) ----
    # Kept for backward compat; not used by the weekly planner.
    sample_weather_profile = [
        CurrentWeatherProfile(
            region="Punjab, Pakistan", season="Rabi",
            avg_temperature_c=26.0, avg_rainfall_mm=2.5, avg_humidity=55.0,
            notes="Stable temperatures, suitable for wheat flowering and ripening.",
            created_at=datetime.utcnow() + timedelta(days=0),
            _start_index=0, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Punjab, Pakistan", season="Rabi",
            avg_temperature_c=27.2, avg_rainfall_mm=3.0, avg_humidity=57.0,
            notes="Slight warming trend observed, no major rainfall expected.",
            created_at=datetime.utcnow() + timedelta(days=1),
            _start_index=1, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Sindh, Pakistan", season="Kharif",
            avg_temperature_c=32.5, avg_rainfall_mm=0.8, avg_humidity=62.0,
            notes="Hot and dry conditions; irrigation planning critical for cotton fields.",
            created_at=datetime.utcnow() + timedelta(days=2),
            _start_index=2, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Sindh, Pakistan", season="Kharif",
            avg_temperature_c=33.1, avg_rainfall_mm=1.2, avg_humidity=65.0,
            notes="Humidity increasing slightly; monitor fungal risk.",
            created_at=datetime.utcnow() + timedelta(days=3),
            _start_index=3, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Khyber Pakhtunkhwa, Pakistan", season="Rabi",
            avg_temperature_c=22.0, avg_rainfall_mm=4.5, avg_humidity=60.0,
            notes="Cooler nights expected; seedling crops may face mild cold stress.",
            created_at=datetime.utcnow() + timedelta(days=4),
            _start_index=4, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Islamabad Capital Territory, Pakistan", season="Rabi",
            avg_temperature_c=24.8, avg_rainfall_mm=5.2, avg_humidity=58.0,
            notes="Intermittent showers forecasted; suitable for soil moisture replenishment.",
            created_at=datetime.utcnow() + timedelta(days=5),
            _start_index=5, _with_increments=7,
        ),
        CurrentWeatherProfile(
            region="Punjab, Pakistan", season="Kharif",
            avg_temperature_c=28.5, avg_rainfall_mm=6.5, avg_humidity=61.0,
            notes="Transition toward Kharif season; early rainfall signals detected.",
            created_at=datetime.utcnow() + timedelta(days=6),
            _start_index=6, _with_increments=7,
        ),
    ]

    db.session.add_all(sample_weather_profile)
    db.session.commit()

    print("Sample data seeded successfully.")
    print(f"Users:        {User.query.count()}")
    print(f"Crops:        {Crop.query.count()}")
    print(f"Fields:       {Field.query.count()}")
    print(f"Tasks:        {Task.query.count()}")
    print(f"Weather rows: {ClimateProfile.query.count()}")
