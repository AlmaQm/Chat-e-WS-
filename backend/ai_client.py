import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
load_dotenv()

_client = AsyncOpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

SYSTEM_PROMPT = (
    "Eres un asistente de IA en un chat grupal. Pueden haber uno o varios usuarios humanos hablando contigo. "
    "Cada mensaje de usuario incluye el nombre de quien lo envió en el formato 'nombre: mensaje'. "
    "Responde siempre como un único asistente de IA, de forma natural y conversacional. "
    "Nunca inventes nombres, nunca te hagas pasar por un usuario humano, nunca simules ser otra persona."
)


async def get_ai_response(history: list[dict]) -> str:
    response = await _client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
    )
    return response.choices[0].message.content
