# Assumptions

The following assumptions have been made to define the scope and boundaries of the current system. These simplifications allow us to focus on core functionality without over-engineering edge cases that are not yet in scope.

## Scheduling

- The farming day begins at 5:00 AM and ends at 7:00 PM local time.
- Daily tasks are generated for one day at a time; the weekly planner covers the current week only.

## Farmer Behaviour

- The farmer always completes all assigned tasks.
- The farmer always follows the generated plan and never rejects a proposed change.
  *(Farmer approval has been bypassed for now as a result of this assumption.)*

## Farm Conditions

- There is no crop damage, pest risk, weed growth, or disease of any kind.
- There is no fertiliser management in the system at this time.
- Crops always have an irrigation need, regardless of current environmental levels.
- Each field has exactly one active crop at a time. Intercropping and staggered rotation scenarios are not supported.
- Crop growth stages are managed manually. The system does not automatically advance a crop from one stage to the next as time passes.
- There are no resource constraints. The system generates tasks without accounting for the farmer's available labour, water supply, or equipment.
- Tasks are fully independent. There are no dependency chains — if one task is delayed, any downstream tasks that logically depend on it are not automatically shifted.

## Geographic Scope

- The system currently supports three regions only: Lahore, Karachi, and Islamabad. Any user outside these cities is mapped to Lahore by default.
- All fields belonging to a farmer are assumed to be in the same region. A farmer with fields in multiple locations receives a single weather profile applied uniformly across all of them.
- Weather is region-based, not coordinate-based. Two farms in the same city receive identical weather data, regardless of how far apart they are.

## Weather & Change Scenarios

- Weather data is at daily resolution only — there is no intra-day variation (e.g. morning dew, afternoon heat peaks, or overnight frost).
- Weather changes only delay tasks — there is never a scenario where a task needs to be moved to an earlier date.
- There are exactly four possible daily weather scenarios:
  - **a.** No change in the weather forecast — no action required.
  - **b.** The forecast changed, but it has no impact on the weekly plan or today's tasks.
  - **c.** The forecast changed and impacts the weekly plan, but today's tasks remain the same.
  - **d.** The forecast changed and impacts both the weekly plan and today's tasks.

## System Behaviour

- All background jobs are assumed to succeed. There are no failure fallbacks or retry mechanisms.
- A request for change history always returns a summarised report for the given date range.

---

# Known Limitations

## Simulated Weather Data

Weather forecasts are currently generated from hardcoded monthly climate profiles rather than a live API. The system simulates realistic conditions for the three supported regions, but this data does not reflect real-time or day-accurate forecasts. Integration with a live weather provider (such as OpenWeatherMap or the Pakistan Meteorological Department) is planned for a future release.

## Geographic Scope — Pakistan Only

The rule base, climate profiles, and risk thresholds are calibrated for Pakistani agricultural conditions. The system is not currently designed to generalise to other countries or climates without significant updates to the rule engine and regional profiles.

## Wind Speed — Tracked but Not Used

Wind speed is recorded in the weather model and stored in the database, but it is not yet factored into risk assessment or planning decisions. High-wind scenarios (which can affect spraying, irrigation efficiency, and crop physical stress) are therefore not detected or acted upon.

## Task Scheduling — Date-Level Only

Tasks are scheduled to a date but not a time of day. In high-heat climates, time-of-day is critical — irrigation and field work performed in peak afternoon heat can be significantly less effective or harmful. This granularity is not yet supported.

## Google AI — HTTP 500 Error

Occasionally, calls to the Gemma model (`gemma-4-26b-a4b-it`) return an HTTP 500 error. This is a server-side issue from Google — the model is a new Gemma 4 Mixture-of-Experts release currently in early access, and its streaming endpoint is not yet fully stable.

The code already handles this gracefully: when streaming fails, it automatically falls back to a standard (non-streaming) `generateContent` call, which works correctly. The chatbot responds as normal — the only difference is that responses appear all at once rather than word by word.

To eliminate these warnings entirely, you could either wait for Google to stabilise the streaming endpoint, or switch to a non-streaming request by default.

---

# Future Work

The following features and improvements are planned for future development iterations.

## Planning & Intelligence

- Allow farmers to regenerate or adjust the weekly plan and daily tasks based on unfinished tasks from previous days.
- Support scenarios where a task needs to be moved to an earlier date, not just delayed.
- Allow farmers to reject or negotiate a proposed plan change.
- Maintain a more detailed and structured change history to support time-series analysis, enabling the system to spot patterns over time and react more quickly and accurately to recurring or evolving conditions.
- Build a complete and detailed change history with full audit trails.

## Weather & Data

- Integrate a live weather API to replace the current simulated forecasts, enabling real-time, location-accurate decision making.
- Add intra-day weather awareness so that tasks can be scheduled at optimal times of day — for example, avoiding field work during peak heat or scheduling irrigation in the early morning.
- Expand geographic support beyond the current three Pakistani cities to cover additional regions and, eventually, other countries with different climate profiles.
- Factor wind speed into the risk assessment and planning pipeline — high winds affect spraying effectiveness, irrigation efficiency, and crop stress.

## Farm Management

- Add full crop growth management, covering:
  - Irrigation scheduling
  - Pest and weed control
  - Fertilisation
- Add a fertilisers and pesticides module.
- Add additional soil measurements such as pH, salinity (EC), sulphur (S), and others.
- Add an irrigation need check (on/off) based on growth stage and current environmental conditions.
- Build a health status dictionary to standardise field and crop health classifications.
- Add a pest detection feature using image processing and AI analysis.
- Add a seed selection process to guide farmers on suitable varieties.
- Add more crop types to the system.

## Planning & Task Intelligence

- Automatically advance crop growth stages as time passes, rather than relying on the farmer to update them manually. This would allow the system to trigger the right tasks at the right stage without human intervention.
- Introduce task dependency chains so that delaying one task (e.g. planting) automatically shifts all dependent tasks (e.g. first irrigation, fertilisation window) accordingly.
- Model resource constraints such as available labour, water supply, and equipment when generating daily tasks, to avoid scheduling more work than is physically achievable in a day.
- Add multi-region farm support so that a farmer with fields in different locations receives region-specific weather data and plans for each field independently.

## Rules & Customisation

- Allow farmers to define their own custom farm rules alongside the generic crop rules.
- Add a rule engine update service to keep the rule base current.
- Once the rule base is sufficiently enhanced, migrate the intelligence layer to a RAG (Retrieval-Augmented Generation) architecture, allowing the AI to reason over a richer, structured knowledge base rather than relying solely on fixed rules.

## UI & Experience

- Make the UI significantly more reactive — changes to tasks, plans, and alerts should reflect in real time without requiring a manual refresh, giving farmers an always-current view of their farm.

## Notifications & Communication

- Add outbound farmer notifications via SMS, email, or mobile push — currently notifications are only visible inside the app and require the farmer to open it.
- Add a job execution audit trail so that it is possible to trace whether a scheduled job ran, when, and with what outcome. This is critical for debugging and for building farmer trust in the system.

## Automation & Jobs

- Add failure fallbacks and retry logic for all background jobs.
- Automatically add a crop to the database when a sowing task is marked as complete from the task UI.
- Add the ability to manage available and planted crops directly from the frontend.
- Refresh the weather database automatically whenever the network is available and the last weather API call was more than a set number of hours ago (e.g. 6 or 12 hours).

## Chatbot & Intent Classification

- Improve intent classification for messages that contain multiple intents, particularly around context extraction.
- Improve intent classification when the intent is carried forward from a previous message in the conversation rather than being explicitly stated in the current one.

## Disaster Management

- Add a disaster management plan tied to each task. Each task should advise on the expected growth stage a crop should be at (e.g. flowering stage 2, with a 2-inch petal). If the crop is not at the expected stage, the farmer can report a problem, and a disaster control service will review previous tasks, rules, and growth stages to identify where things may have gone wrong and recommend corrective actions.
