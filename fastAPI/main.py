import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from groq import Groq
from location_tool import find_places

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

HISTORY_FILE = "data/history.json"
os.makedirs("data", exist_ok=True)

SYSTEM_PROMPT = (
    "You are a helpful voice assistant. When asked for places in a city (such as pharmacies, restaurants, "
    "bars, supermarkets, metro stations, or schools), always use the find_places tool. "
    "Format your final response as a clear, polite numbered list of 5 places. "
    "For each item, give only the real NAME and the verified ADDRESS from the tool (do NOT include distances). "
    "Keep it concise, clear, and easy to understand when spoken aloud."
)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if history and history[0].get("role") == "system":
                    history[0]["content"] = SYSTEM_PROMPT
                    return history
        except Exception:
            pass
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def save_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


messages = load_history()


class Question(BaseModel):
    message: str


tools = [
    {
        "type": "function",
        "function": {
            "name": "find_places",
            "description": "Find a list of 5 places (pharmacies, bars, restaurants, supermarkets, etc.) in a city using Google Maps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The category or place type, e.g. 'pharmacies', 'bars', 'restaurants', 'supermarkets', 'metro stations'",
                    },
                    "city": {
                        "type": "string",
                        "description": "The city to search in, e.g. 'Naples', 'Rome', 'Milan', 'Paris'. Default to 'Naples' if none specified.",
                    },
                },
                "required": ["category"],
            },
        },
    }
]


@app.get("/")
def root():
    return {"status": "Chatbot API is running"}


@app.post("/chat")
def chat(q: Question):
    messages.append({"role": "user", "content": q.message})

    while True:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools,
            max_tokens=1000,
            reasoning_effort="low",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in msg.tool_calls
            ],
        })

        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments)
            except Exception:
                args = {}

            category = args.get("category", q.message)
            city = args.get("city", "Naples")

            places = find_places(category=category, city=city)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(places, ensure_ascii=False),
            })

    reply = (msg.content or "").strip()
    messages.append({"role": "assistant", "content": reply})
    save_history(messages)
    return {"reply": reply}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    result = client.audio.transcriptions.create(
        file=(file.filename, audio_bytes),
        model="whisper-large-v3-turbo",
    )
    return {"text": result.text.strip()}
