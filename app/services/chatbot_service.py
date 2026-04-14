from .gemma_service import ask_gemma

def get_chat_response(user_message):
    prompt = f"""
    You are a farming assistant.

    Farmer question:
    {user_message}

    Give simple, clear advice.
    """

    return ask_gemma(prompt)