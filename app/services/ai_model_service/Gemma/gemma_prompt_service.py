def build_recommendation_prompt(weather: dict, soil: dict, crop: dict) -> str:
    return f"""
You are an expert agricultural climate adaptation advisor.

Your job is to help a farmer using simple, practical language.
The farmer may have limited technical knowledge, so avoid jargon.
Focus on immediate actions, seasonal planning, and climate adaptation.

Input data:
Weather:
{weather}

Soil:
{soil}

Crop:
{crop}

Please provide:
1. A short summary of the current farming situation
2. 3 to 5 recommended actions
3. Any important risks or alerts
4. A simple planting or care suggestion based on current conditions

Keep the response concise, practical, and farmer-friendly.
""".strip()


def build_chat_prompt(
    user_input: str,
    weather: dict,
    soil: dict,
    crop: dict,
    tasks: list = None,
) -> str:
    task_section = ""
    if tasks:
        task_lines = []
        for t in tasks[:6]:
            line = f"- [{t.get('priority','?').upper()}] {t.get('title','?')}"
            if t.get("description"):
                line += f": {t['description']}"
            task_lines.append(line)
        task_section = "\n\nPending tasks:\n" + "\n".join(task_lines)

    return f"""You are a smart farming assistant. Answer in 2–5 sentences. Use the exact data given.

Farmer question: {user_input}

Farm context:
Weather: {weather}
Soil: {soil}
Crop: {crop}{task_section}

Rules:
- If the farmer questions why a task was recommended: cite the specific weather or soil number that triggered it
- If they push back on timing ("we never do this in May"): acknowledge their experience, then explain what changed this year using the forecast or sensor data
- No generic advice when you have actual numbers

Answer:""".strip()



def build_task_alert_prompt(weather: dict, soil: dict, crop: dict) -> str:
    return f"""
You are an agricultural advisor for farmers affected by climate change.

Analyze this data and produce:
1. urgent alerts
2. today's tasks
3. short reasons for each task

Weather:
{weather}

Soil:
{soil}

Crop:
{crop}

Rules:
- Keep language very simple
- Output only practical actions
- Prioritize risk prevention
- Assume the farmer is not highly technical
""".strip()



def build_season_plan_prompt(farm_info: dict) -> str:
    return f"""
You are a climate adaptation planning assistant for farmers.

Based on this farm information, create:
1. a season plan
2. a simple timeline
3. planting advice
4. mitigation steps for climate risk

Farm info:
{farm_info}

Keep the answer practical, simple, and easy to follow.
""".strip()