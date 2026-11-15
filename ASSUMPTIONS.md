# Assumptions

The following assumptions define the current scope and operational boundaries of the system. These simplifications allow the platform to focus on core climate-adaptive planning functionality without over-engineering edge cases that are outside the current project scope.

---

## Scheduling

- The farming day begins at **5:00 AM** and ends at **7:00 PM** local time.
- Daily tasks are generated one day at a time.
- The weekly plan is a rolling 7-day window starting today.
  - The 5:00 AM daily update regenerates it every morning (today..today+6) from the unchanged seasonal plan, then applies the forecast.
  - The Monday 3:30 AM weekly plan job is still scheduled but now redundant: the daily update already rolls the plan every day.

---

## Farmer Behaviour

- The farmer always completes all assigned tasks.
- The farmer always follows the generated plan and never rejects a proposed change.
  - *Farmer approval workflows are intentionally bypassed in the current implementation.*

---

## Farm Conditions

- There is no crop damage, pest outbreak, weed growth, or disease event in the current system.
- Fertiliser management is not yet supported.
- Crops are always assumed to require irrigation regardless of environmental moisture conditions.
- Each field contains exactly one active crop at a time.
  - Intercropping and staggered crop rotation are not currently supported.
- Crop growth stages are updated manually.
  - The system does not automatically progress crops through lifecycle stages over time.
- Resource constraints are ignored.
  - Labour availability, water limitations, and equipment availability are not considered during planning.
- Tasks are treated as fully independent.
  - Delaying one task does not automatically shift downstream dependent tasks.

---

## Geographic Scope

- The system currently supports only:
  - Lahore
  - Karachi
  - Islamabad
- Users outside these cities are mapped to Lahore by default.
- All fields belonging to a farmer are assumed to exist within the same geographic region.
- Weather is region-based rather than coordinate-based.
  - Two farms within the same city receive identical weather conditions regardless of physical distance.

---

## Weather & Climate Scenarios

- Weather data is evaluated at daily resolution only.
  - Intra-day conditions such as morning dew, afternoon heat peaks, or overnight frost are not modelled.
- Weather changes can only delay tasks.
  - Tasks are never moved earlier than originally scheduled.
- The system currently supports exactly four weather-change scenarios:

| Scenario | Description |
|---|---|
| **A** | No weather change — no action required |
| **B** | Forecast changed, but no impact on planning or tasks |
| **C** | Forecast changed and impacts the weekly plan only |
| **D** | Forecast changed and impacts both the weekly plan and daily tasks |

---

## Demo Scenario: Pre-Sowing Decision

- **The rule base covers Kharif crops** (Maize, Rice, Cotton), which are sown roughly April–July.
  Outside that season (e.g. in November) no day is suitable for sowing them, which is the correct answer.
- **The demo runs on a simulated date in the Kharif season** (demo clock):
  - `DEMO_TODAY=YYYY-MM-DD` in the environment (e.g. `2027-05-05`) sets "today" for planning, weather,
    tasks, jobs and seeders. Empty or unset means the real date.
  - Timestamps (created at, job start/end) keep the real time.
  - The UI shows a banner such as "Demo date: 5 May 2027 (Kharif season)" when it is set.
- **Rabi crops** (wheat, chickpea) are a data addition for later: crop and rulebook values validated by an agronomist.
- The demo represents a farmer **planning to sow this week**, not a crop already in the ground.
  - Seeded sowing dates are set relative to today (today to today + 2), so they always fall inside the simulator's week.
  - The demo weather is realistic for early May in Punjab (hot, dry, long sunshine) with a two-day western
    disturbance that the rules reject for Cotton sowing. Nothing in it is hand-picked for a crop.
- The whole seasonal plan uses the growth stage **Sowing**.
  - The rulebook lookups and the seeded demo weather were designed for this stage (e.g. a cold spell → "delay sowing by 4 days").
- **Why not sowing dates in the past?** In real farming, sowing usually happened earlier, and that is valid.
  But a past sowing date combined with the fixed "Sowing" stage would be inconsistent, and sowing-stage rules
  (such as delaying sowing) have nothing to act on once sowing is over.
- **Intended future behaviour:**
  - The farmer enters the actual sowing date per field.
  - The growth stage advances automatically based on days since sowing.
  - The rules for the current stage apply, so mid-season weather triggers stage-specific changes
    (e.g. more irrigation during flowering in a heatwave).

---

## Planned vs Actual Dates (Plan Event Overrides)

- The **seasonal plan holds the planned dates** and is never changed by daily operations.
- **Actual dates** live in a separate layer, `PlanEventOverride`, one row per change of a one-time event
  (sowing, fertilization, harvesting, irrigation start):
  - `forecast_shift`: a forecast rule moved the event (e.g. "Sowing delayed by 4 days — unfavourable sunlight conditions").
    A sowing delay also moves harvest, irrigation start and fertilization by the same number of days.
  - `farmer_completed`: the farmer marked the sowing task done; the actual sowing date is the completion date, and
    harvest, irrigation start and fertilization move by the difference to the previous sowing date (the date the plan
    showed until then, which may already include a forecast shift).
    Un-completing the task removes these rows again.
- The weekly plan is built from **effective dates**: the latest override per event, otherwise the seasonal date.
  Irrigation repeats from the effective irrigation start until the effective harvest date.
- **The farmer beats the forecast:** once sowing is recorded as done, it is no longer an upcoming event and the
  forecast cannot shift it; a later forecast can still move harvest.
- Every override stores the day of the decision (`as_of_date`). When planning for a day, that day's own forecast
  decisions are recalculated, not re-applied, so running the daily update or the simulator twice gives the same result.
- Temporary adjustments (extra or removed irrigation sessions, "avoid this window") are **not** stored; they are
  recalculated every day from the forecast.
- **Extra irrigation sessions** (e.g. a dry week: rainfall <50 mm → "irrigation increase days") are only placed on
  free days from the effective irrigation start up to the day before the effective harvest, never before sowing.
  If no day of the plan window qualifies, the plan says so, e.g. "Dry week: no extra irrigation – irrigation starts
  13 May". Pre-sowing irrigation (rauni) is not modelled yet.
- **Sowing window:** each crop has a sowing window from the planned (seasonal) sowing date to
  planned + `MAX_SOWING_DELAY_DAYS` (14 days, a **placeholder until validated by an agronomist**).
  - Every day the plan picks the **first suitable day** in the window within the visible forecast (today..today+6):
    a day where none of the crop's sowing-stage rules (temperature, humidity, sunlight, rainfall, soil moisture, pH)
    says "delay sowing" or "avoid". Rules don't add up — a day is suitable or not.
  - It is recalculated from scratch every day, so sowing can move **earlier** again when the forecast improves,
    but never before the planned date and never before today.
  - No suitable day in the forecast: sowing is provisionally the first window day after the forecast, with
    "No suitable sowing day in the forecast – re-checked daily".
  - **No suitable day left in the window** (the window end is in the forecast and no remaining day is suitable):
    sowing is **not** scheduled on an unsuitable day. The crop shows "No suitable sowing day left in the sowing
    window – decision needed" with the same options as overdue; it is re-checked daily until the window ends.
  - Harvest, irrigation start and fertilization follow the effective sowing date. A completed sowing (farmer) is never
    moved.
- **Sowing overdue → human decision:** when the window has passed and sowing was not completed, the crop stays in the
  weekly plan as "Sowing overdue – decision needed" (no sowing, irrigation or fertilization events) with the options:
  sow anyway with precautions, switch to a short-duration variety, switch crop, or skip the season. The system does
  not choose. **One notification per crop** (decision needed or overdue, whichever comes first) is sent **on the day it
  happens**, also on days without a plan impact.
- **The daily update always applies the forecast to the weekly plan** (sowing window, actual dates). This step makes no
  AI calls; its only notification is the sowing decision above. Other notifications, task updates and AI summaries
  only follow on days with a plan impact (plus the existing weather-only notification on "change without impact" days).
- A same-day rebuild without the forecast (weekly job, app restart) shows that day's plan without its forecast
  decisions until the next daily update or simulator run.
- **Demo:** overrides are deleted together with the seasonal plans when the app restarts and reseeds (`run.py`),
  so actual dates do not survive a restart.

---

## System Behaviour

- All background jobs are assumed to succeed successfully.
- Retry mechanisms and failure recovery workflows are not currently implemented.
- Change-history requests always return summarised reports for the selected date range.

---

# Known Limitations

---

## Simulated Weather Data

Weather forecasts are currently generated using hardcoded monthly climate profiles rather than a live weather API.

The system simulates realistic climate conditions for the supported regions, but the forecasts are not:
- real-time
- location-accurate
- day-accurate

Future versions will integrate live weather providers such as:
- OpenWeatherMap
- Pakistan Meteorological Department APIs

---

## Geographic Scope — Pakistan Only

The rule base, climate profiles, and agricultural thresholds are calibrated specifically for Pakistani farming conditions.

The current implementation is not intended to generalise globally without:
- regional climate tuning
- updated agricultural rule sets
- localisation adjustments

---

## Wind Speed — Tracked but Not Used

Wind speed data is stored in the system but is not currently used in:
- planning
- risk analysis
- recommendation generation

As a result, the platform does not yet respond to:
- high-wind irrigation inefficiencies
- spraying risks
- wind-induced crop stress

---

## Task Scheduling — Date-Level Only

Tasks are scheduled by date only, not by time-of-day.

This limits the system’s ability to optimise work around:
- peak daytime heat
- ideal irrigation timing
- temperature-sensitive operations

---

## Google AI — HTTP 500 Error

Occasionally, calls to the Gemma model (`gemma-4-26b-a4b-it`) may return HTTP 500 errors.

This is a server-side issue related to the current early-access release of the Gemma 4 Mixture-of-Experts model and its streaming endpoint stability.

The system already handles this gracefully:
- failed streaming requests automatically fall back to standard non-streaming `generateContent` calls
- chatbot functionality continues normally
- responses simply appear all at once instead of streaming token-by-token

Potential long-term fixes include:
- waiting for Google to stabilise the streaming endpoint
- switching permanently to non-streaming responses

---

# Future Work

The following improvements and extensions are planned for future development iterations.

---

## Planning & Intelligence

- Allow farmers to regenerate weekly plans based on unfinished tasks.
- Support advancing tasks earlier when weather conditions require it.
- Allow farmers to:
  - reject
  - negotiate
  - modify
  proposed plan changes.
- Expand change-history tracking into a complete time-series intelligence system.
- Build full audit trails for all planning modifications.

---

## Weather & Climate Intelligence

- Integrate live weather APIs for real-time forecasting.
- Add intra-day weather awareness for:
  - heat-sensitive scheduling
  - optimal irrigation timing
  - safer field operations
- Expand geographic support beyond the current three cities.
- Add wind-speed-aware planning and risk analysis.

---

## Farm Management

- Add full crop growth management including:
  - irrigation scheduling
  - pest management
  - weed control
  - fertilisation
- Add fertiliser and pesticide modules.
- Add advanced soil metrics:
  - pH
  - salinity (EC)
  - sulphur
  - nutrient tracking
- Add environmental irrigation-need checks.
- Build a standardised crop-health classification system.
- Add AI-powered pest detection using image analysis.
- Add crop variety and seed recommendation workflows.
- Expand crop support coverage.

---

## Planning & Task Intelligence

- Automatically advance crop growth stages over time.
- Introduce task dependency chains.
- Model resource constraints including:
  - labour
  - water
  - equipment
- Support multi-region farms with field-specific weather planning.

---

## Rules & Customisation

- Allow farmers to define custom operational rules.
- Add automated rule-engine update workflows.
- Migrate the intelligence layer toward a RAG (Retrieval-Augmented Generation) architecture for richer contextual agricultural reasoning.

---

## UI & User Experience

- Make the interface significantly more reactive and real-time.
- Ensure plans, alerts, and tasks update instantly without manual refreshes.

---

## Notifications & Communication

- Add:
  - SMS notifications
  - email notifications
  - push notifications
- Build job execution audit trails for debugging and operational transparency.

---

## Automation & Background Jobs

- Add:
  - retry logic
  - fallback mechanisms
  - job-failure recovery
- Automatically register crops after sowing completion.
- Add frontend crop management workflows.
- Automatically refresh weather datasets periodically whenever internet connectivity is available.

---

## Chatbot & Intent Classification

- Improve multi-intent understanding.
- Improve conversational context retention across messages.
- Enhance context extraction for agricultural conversations.

---

## Disaster Management

- Add disaster-management workflows tied to crop growth stages.
- Allow farmers to report abnormal crop development.
- Build AI-assisted diagnosis workflows that analyse:
  - historical tasks
  - crop stages
  - environmental conditions
  - operational history

to identify potential causes and recommend corrective actions.
