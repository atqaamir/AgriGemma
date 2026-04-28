from .gemma_service import ask_gemma

class ChatbotService:

    @staticmethod
    def get_chat_response(user_message):
        prompt = f"""
        You are a farming assistant.

        Farmer question:
        {user_message}

        Give simple, clear advice.
        """

        return ask_gemma(prompt)
    

    
    """
    NOTE:
    The only thing I’d keep firm is:

        chatbot should use planner/recommendation services
        not bypass them to read rules directly
    
    
    """