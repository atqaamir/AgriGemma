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


_GENERAL_NOTE = (
    "This is a general question. The farm data above is background context only — "
    "draw primarily on your expert agricultural knowledge and the web search results below "
    "to answer fully and practically. Don't limit your answer to what the farm data says."
)

_GENERAL_NOTE_NO_WEB = (
    "This is a general question. The farm data above is background context only — "
    "draw primarily on your expert agricultural knowledge to answer fully and practically. "
    "Don't limit your answer to what the farm data says."
)


def _web_block(web_results: list[dict]) -> str:
    lines = ["WEB SEARCH RESULTS:"]
    for i, r in enumerate(web_results, 1):
        title   = r.get("title", "")
        snippet = r.get("snippet", "")
        lines.append(f"[{i}] {title}: {snippet}")
    return "\n".join(lines)


def build_chatbot_prompt(
    farmer_context: str,
    history: str,
    user_message: str,
<<<<<<< HEAD
    language: str = 'en',
=======
    intent: str = "general",
    web_results: list | None = None,
>>>>>>> main
) -> str:
    system = CHATBOT_SYSTEM + (_URDU_ADDENDUM if language == 'ur' else "")
    user_parts = [f"FARM DATA:\n{farmer_context}"]

    if web_results:
        user_parts.append(_web_block(web_results))

    if history.strip():
        user_parts.append(f"CONVERSATION:\n{history}")

    question_block = f"FARMER ASKS: {user_message}"
    if intent == "general":
        note = _GENERAL_NOTE if web_results else _GENERAL_NOTE_NO_WEB
        question_block += f"\n\nNOTE: {note}"

    user_parts.append(
        f"{question_block}\n\n"
        "Reply in the same format as the examples above. One line only."
    )

    user_content = "\n\n".join(user_parts)
    return f"{system}{_SYSTEM_SEP}{user_content}"
