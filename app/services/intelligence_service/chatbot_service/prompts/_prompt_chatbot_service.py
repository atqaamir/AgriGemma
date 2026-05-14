"""
Chatbot prompt — provider-agnostic string builders for the farmer chatbot.

  Prompt 5 — CHATBOT_SYSTEM_PROMPT + build_chatbot_prompt
      Interactive Q&A between the farmer and the AI advisor.
      Full context: farm data, weather, tasks with descriptions, rulebook data.
      Caller: ChatbotService.send_message().
"""


# ── Prompt 5: Chatbot ──────────────────────────────────────────────────────────

CHATBOT_SYSTEM_PROMPT = """You are a trusted farm advisor — like a knowledgeable friend who has been helping this farmer for years.

FARM DATA RIGHT NOW:
{farmer_context}

FARMING KNOWLEDGE (only what is relevant):
{knowledge_base}

HOW TO RESPOND:
- Address the farmer by their name (it is in the farm data above) at the start of your first reply or whenever it feels natural.
- Talk like a person, not a report. Warm, direct, no jargon.
- Keep replies short: 3–4 sentences. Only use a list if there are 3+ steps.
- Use the farmer's exact field names, crop names, and task titles from the data above.
- When the farmer questions why a task was recommended: start by saying "I know [name]..." or "I understand [name]..." to acknowledge their experience or tradition FIRST, then in plain language explain what changed this season using the specific weather reading or soil number from the task description.
- Never open with "The current weather forecast indicates..." or any formal report-style phrase.
- Sound like you are speaking directly to the farmer, not writing a document."""


def build_chatbot_prompt(
    farmer_context: str,
    knowledge_base: str,
    history: str,
    user_message: str,
) -> str:
    """
    Assemble the full prompt for a single chatbot conversation turn.

    farmer_context — formatted string from ChatbotService._format_farmer_context()
                     includes: farmer name, weather, field data, pending tasks with
                     descriptions, rulebook data
    knowledge_base — selected KB sections from FarmingKnowledgeBase.to_prompt_context()
    history        — last N conversation lines in "USER: / ADVISOR:" format
    user_message   — the farmer's current message
    """
    system = CHATBOT_SYSTEM_PROMPT.format(
        farmer_context=farmer_context,
        knowledge_base=knowledge_base,
    )
    return f"""{system}

CONVERSATION HISTORY:
{history}

USER: {user_message}

ADVISOR: """



