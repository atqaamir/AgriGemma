# Assumptions

The following assumptions define the current scope and operational boundaries of the system. These simplifications allow the platform to focus on core climate-adaptive planning functionality without over-engineering edge cases that are outside the current project scope.

---

## Scheduling

- The farming day begins at **5:00 AM** and ends at **7:00 PM** local time.
- Daily tasks are generated one day at a time.
- The weekly planner only covers the current week.

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
