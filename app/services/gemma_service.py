import requests

GEMMA_API_URL = "YOUR_GEMMA_ENDPOINT"

def ask_gemma(prompt):
    response = requests.post(
        GEMMA_API_URL,
        json={"prompt": prompt}
    )

    return response.json()