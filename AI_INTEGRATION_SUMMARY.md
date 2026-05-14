# AI Integration & Task Generation Refactor

## Summary
Removed caching from task intelligence generation and fully integrated Gemma AI into the task generation, task intelligence, and notification pipelines. All AI recommendations are now persisted to the database at generation time, with fresh Gemma calls on every dashboard/task page load.

---

## Changes Made

### 1. **TaskIntelligenceService** (`app/services/intelligence_service/task_intelligence_service.py`)
**Before:** Cached full task intelligence response (300s TTL) per user.  
**After:** No caching. Fresh Gemma calls on every request.

**New Methods:**
- `generate_task_overview(context, user_id)` → Returns one-liner summary of critical tasks for Tasks page header
- `generate_task_explanation(task, context)` → Explains why a specific task was generated; result stored in `Task.ai_explanation` at creation time
- `invalidate_cache()` → No-op for backward compatibility

**Fallback Behavior:**
- Rule-based intelligence if Gemma unavailable, never blank
- `_build_task_overview_fallback()` for task overview summary
- `_build_rule_based_fallback()` for full intelligence JSON

---

### 2. **TaskGenerationService** (`app/services/task_generation_service.py`)
**Before:** Placeholder that returned text strings like "Irrigation needed".  
**After:** AI-driven task generation that creates persistent Task records with explanations.

**New Logic:**
1. Collect active fields, weekly plan, seasonal plan, existing tasks
2. For each condition (low moisture, poor health, growth stage review, weekly tasks):
   - Check if task title already exists (dedup)
   - Create Task record with title, priority, description
   - **Call `TaskIntelligenceService.generate_task_explanation()` to get AI reasoning**
   - Persist explanation to `Task.ai_explanation` in database
3. Return dict: `{created: N, task_ids: [...], seasonal_plan, weekly_plan}`

**Replaces manual rule-based task generation.**

---

### 3. **DashboardService** (`app/services/dashboard_service.py`)
**Before:** Placeholder `_build_ai_insights()` that returned hardcoded string.  
**After:** Calls `TaskIntelligenceService.generate_intelligence()` to get fresh Gemma-generated dashboard summary.

**Updated Dashboard Data:**
- `dashboard_summary` — AI-generated 2-3 sentence farm overview
- `dashboard_recommendations` — List of AI-generated actionable recommendations
- `insights` — Array of AI observations from the full intelligence JSON

**All via fresh Gemma call on every dashboard load.**

---

### 4. **NotificationService** (`app/services/domain_service/notification_service.py`)
**Before:** `generate_alerts()` detected alerts but only logged explanations; didn't persist them.  
**After:** Creates Notification records with AI-generated `detail` field on every call.

**New Logic:**
- `generate_alerts(user_id, tag)` → Detects alerts + generates batch AI explanation → Creates Notification records with detail
- `generate_notifications(user_id, tag)` → Wrapper for backward compat with NotificationAgent
- `generate_alert_for_user(user_id, context)` → Direct consumer interface; returns created notification IDs

**First alert in batch gets full explanation; others get individual alert message.**

---

### 5. **IntelligenceAgent** (`app/agents/intelligence_agent.py`)
**Before:** `generate(user_id)` → always called `generate_intelligence()`  
**After:** Supports tag parameter to dispatch to different intelligence methods.

**Routes:**
- `tag=None` or `tag="full"` → `TaskIntelligenceService.generate_intelligence()` (full farm overview)
- `tag="critical_task_overview"` → `TaskIntelligenceService.generate_task_overview()` (Tasks page header)

---

### 6. **CoordinatorAgent** (`app/agents/coordinator_agent.py`)
**Before:** `generate_task_intelligence()` was commented out.  
**After:** Uncommented and active; orchestrates task intelligence generation.

**Coordinator Workflows:**
- `daily_update()` calls `call_intelligence(user_id, tag="critical_task_overview")` after task generation
- Always refreshes dashboard at end (`dashboard_refresh()`)
- Fallback JSON returned on any exception

---

### 7. **PlanningAgent** (`app/agents/planning_agent.py`)
**Before:** Methods had incompatible signatures (field_id, context).  
**After:** Updated to match coordinator signatures.

**Methods:**
- `generate_daily_tasks(user_id, tag="")` → Status.SUCCESS/FAILED
- `generate_seasonal_plan(user_id, tag="")` → Status.SUCCESS/FAILED

---

### 8. **ContextAggregationService** (`app/services/intelligence_service/chatbot_service/context_aggregation_service.py`)
**Added Collectors:**
- `_collect_seasonal_plan(user_id)` → SeasonalPlannerService
- `_collect_weekly_plan(user_id)` → WeeklyPlannerService

**Context now includes:** seasonal_plan, weekly_plan

---

### 9. **Task Route** (`app/routes/_page_tasks.py`)
**Removed:** TaskEventService.on_task_change() calls (no longer needed; AI explanations persisted at creation time)

**Route:** `GET /intelligence` → Calls `coordinator.generate_task_intelligence(user_id)` → Returns TaskIntelligenceSchema

---

### 10. **Task Model** (`app/models/task.py`)
**Unchanged**, but now utilized:
- `ai_explanation` field persisted when task created by `TaskGenerationService`

---

## Data Flow

### Task Generation Pipeline
```
CoordinatorAgent.task_generation(user_id)
  → PlanningAgent.generate_daily_tasks(user_id)
    → TaskGenerationService.generate_daily_tasks(user_id)
      1. Collect fields, plans, context
      2. For each condition, create Task record
      3. Call TaskIntelligenceService.generate_task_explanation(task, context)
      4. Persist Task.ai_explanation to DB
      → Return {created: N, task_ids: [...]}
  → DashboardAgent.refresh_dashboard(user_id)
  → call_intelligence(user_id, tag="critical_task_overview")
    → TaskIntelligenceAgent.generate(user_id, tag="critical_task_overview")
      → TaskIntelligenceService.generate_task_overview(context, user_id)
        → Calls Gemma with build_critical_tasks_overview_prompt
        → Returns one-liner for Tasks page header
```

### Dashboard Pipeline
```
GET /dashboard/<user_id>
  → DashboardService.build_dashboard_data(user_id)
    1. Collect fields, tasks, crops, weather, etc.
    2. Build context via ContextAggregationService
    3. Call TaskIntelligenceService.generate_intelligence(context, user_id)
       → Calls Gemma with build_dashboard_summary_prompt
       → Returns {summary, priority_level, recommendations, urgent_actions, risks, insights}
    4. Include in dashboard_data:
       - dashboard_summary
       - dashboard_recommendations
       - insights
    → Return full dashboard JSON
```

### Notification Pipeline
```
CoordinatorAgent.send_notification(user_id, tag=tag)
  → NotificationAgent.generate_notifications(user_id, tag=tag)
    → NotificationService.generate_notifications(user_id, tag=tag)
      1. Call _detect_from_context(context)
      2. Call _generate_ai_explanation(alerts, context) [fresh Gemma]
      3. For each alert, create Notification record with:
         - title/message = alert.message
         - detail = AI explanation (first alert) or individual alert (rest)
         - notification_type = CRITICAL or WARNING
      → Return Status.SUCCESS
```

---

## Fallback Behavior

**All three pipelines have rule-based fallbacks:**

1. **TaskIntelligenceService:**
   - `_build_task_overview_fallback()` — Returns count + priority summary
   - `_build_rule_based_fallback()` — Returns full intelligence JSON with rules-based logic

2. **TaskGenerationService:**
   - Falls back to per-field rule checks if context aggregation fails

3. **NotificationService:**
   - `_generate_ai_explanation()` returns rule-based explanation if Gemma fails

4. **Dashboard:**
   - Falls back gracefully if any service fails; dashboard still renders with partial data

---

## Database Persistence

**Persisted AI Outputs:**
- **Task.ai_explanation** — Persisted when task generated by TaskGenerationService
- **Notification.detail** — Persisted when alert detected by NotificationService

**No caching, no TTL** — Every request triggers fresh Gemma calls.

---

## Testing Checklist

- [ ] Task generation creates tasks with `ai_explanation` populated
- [ ] Dashboard page renders with AI-generated summary, recommendations, insights
- [ ] Tasks page header shows critical tasks overview one-liner
- [ ] Notifications created with AI-generated detail field
- [ ] Fallback activates gracefully when Gemma unavailable
- [ ] CoordinatorAgent daily_update workflow completes successfully
- [ ] No stale cached intelligence appears

---

## Related Files (Not Modified)

- `app/services/intelligence_service/chatbot_service/prompts/_prompt_task_intelligence.py` — Prompt builders already in place
- `app/models/task.py` — ai_explanation field already defined
- `app/models/notification.py` — detail field already defined
- `app/repositories/task_repository.py` — No changes needed
- `app/repositories/notification_repository.py` — No changes needed
