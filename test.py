import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# Consulta a lista oficial de modelos ativos na sua conta
modelos = client.models.list()
print("Modelos ativos no Groq:")
for m in modelos.data:
    print(f"- {m.id}")
