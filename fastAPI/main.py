import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

# HISTORY_FILE = "history.json"
HISTORY_FILE = "data/history.json"
os.makedirs("data", exist_ok=True)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"role": "system", "content": "You are a helpful voice assistant. Keep answers short."}]


def save_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


messages = load_history()


class Question(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "Chatbot API is running"}


@app.post("/chat")
def chat(q: Question):
    messages.append({"role": "user", "content": q.message})
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        max_tokens=1000,
        reasoning_effort="low",
    )
    reply = (response.choices[0].message.content or "").strip()
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