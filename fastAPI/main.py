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


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {
            "role": "system",
            "content": "You help people find places and addresses. When asked where something is, use the find_place tool. Answer in one or two short spoken sentences. Never read coordinates aloud.",
        }
    ]


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
            "name": "find_place",
            "description": "Find places or addresses on a map.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "e.g. 'pharmacy near Via Toledo, Naples'",
                    }
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

        # If the model didn't request a tool call, we have our final text reply
        if not msg.tool_calls:
            break

        # Record assistant tool request
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

        # Execute the tool (Nominatim lookup) for each call
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            places = find_place(args["query"])
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
