"""
Chatbot prompt builder.

Format compliance is enforced by a few-shot user→model example injected in
google_ai_provider._payload(), not by instructions in the prompt. This means:
  - No format description needed here (avoids contradictions the model argues with)
  - System instruction stays short — only persona + data-use rules
  - User turn is clean: farm data, optional history, farmer's question
"""

_SYSTEM_SEP = "\x00SYS\x00"

CHATBOT_SYSTEM = (
    "You are a warm, direct farm advisor.\n"
    "1. Use exact field names, crop names, and numbers from the farm data.\n"
    "2. Use your general agricultural knowledge when the data does not cover the question.\n"
    "3. Do not start every reply with the farmer's name — use it naturally, not as an opener.\n"
    "4. When the farmer questions a task, start with 'I know...' or 'I understand...' then explain with specific data.\n"
    "5. When RULEBOOK DATA is present, cite the exact number instead of giving generic advice."
)

# Appended to CHATBOT_SYSTEM when the UI language is Urdu
_URDU_ADDENDUM = (
    "\n6. The farmer is using the Urdu interface. YOU MUST reply ENTIRELY in Urdu (اردو). "
    "Use plain, simple Urdu suitable for a Pakistani farmer. Field names, crop names, and "
    "numerical values may remain as given in the farm data, but every explanation, suggestion, "
    "and sentence MUST be written in Urdu script. Do not mix in English sentences."
)


def build_chatbot_prompt(
    farmer_context: str,
    history: str,
    user_message: str,
    language: str = 'en',
) -> str:
    system = CHATBOT_SYSTEM + (_URDU_ADDENDUM if language == 'ur' else "")
    user_parts = [f"FARM DATA:\n{farmer_context}"]

    if history.strip():
        user_parts.append(f"CONVERSATION:\n{history}")

    user_parts.append(
        f"FARMER ASKS: {user_message}\n\n"
        "Reply using ONLY this format:\n"
        "{RESPONSE: '<your answer>', URGENCY: '<low|medium|high>', ACTIONS: '<action1 | action2 | NONE>'}\n"
        "One line. No text outside the curly braces."
    )

    user_content = "\n\n".join(user_parts)
    return f"{system}{_SYSTEM_SEP}{user_content}"
