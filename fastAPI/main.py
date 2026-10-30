import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from groq import Groq
from location_tool import find_place

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

HISTORY_FILE = "data/history.json"
os.makedirs("data", exist_ok=True)

SYSTEM_PROMPT = (
    "You are a helpful voice assistant. You help people find places and addresses. "
    "When asked where something is or for the nearest place, use the find_place tool. "
    "Answer in one or two short spoken sentences, clearly stating the name, how far away it is "
    "(e.g. '150 meters away' or '1.2 km away'), and the street name. "
    "Never read raw GPS coordinates aloud."
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
    latitude: float | None = None
    longitude: float | None = None


tools = [
    {
        "type": "function",
        "function": {
            "name": "find_place",
            "description": (
                "Search for places, shops, or addresses. When user coordinates (user_lat, user_lon) "
                "are provided, results are sorted by physical distance to return the closest ones."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Place or business name, e.g. 'pharmacy', 'Sole 365', 'supermarket', 'school', 'train station'",
                    },
                    "user_lat": {
                        "type": "number",
                        "description": "User's current latitude.",
                    },
                    "user_lon": {
                        "type": "number",
                        "description": "User's current longitude.",
                    },
                },
                "required": ["query"],
            },
        },
    }
]


@app.get("/")
def root():
    return {"status": "Chatbot API is running"}


@app.post("/chat")
def chat(q: Question):
    user_text = q.message
    if q.latitude is not None and q.longitude is not None:
        user_content = f"{user_text}\n[My current location coordinates: {q.latitude}, {q.longitude}]"
    else:
        user_content = user_text

    messages.append({"role": "user", "content": user_content})

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

            lat = args.get("user_lat") if args.get("user_lat") is not None else q.latitude
            lon = args.get("user_lon") if args.get("user_lon") is not None else q.longitude
            query = args.get("query", user_text)

            places = find_place(query=query, user_lat=lat, user_lon=lon)
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
