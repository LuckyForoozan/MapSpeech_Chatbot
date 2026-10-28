# import json
# import os
# from dotenv import load_dotenv
# from groq import Groq
# import pyttsx3
# from scipy.io.wavfile import write
# import sounddevice as sd

# load_dotenv()
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# HISTORY_FILE = "history.json"


# def load_history():
#     if os.path.exists(HISTORY_FILE):
#         with open(HISTORY_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return [
#         {
#             "role": "system",
#             "content": "You are a helpful voice assistant. Keep answers short.",
#         }
#     ]


# def save_history(messages):
#     with open(HISTORY_FILE, "w", encoding="utf-8") as f:
#         json.dump(messages, f, ensure_ascii=False, indent=2)


# def speak(text):
#     engine = pyttsx3.init()
#     engine.say(text)
#     engine.runAndWait()


# messages = load_history()
# fs = 16000

# while True:
#     print("Speak now (10 seconds)...")
#     audio = sd.rec(int(10 * fs), samplerate=fs, channels=1, dtype="int16")
#     sd.wait()
#     write("test.wav", fs, audio)

#     with open("test.wav", "rb") as f:
#         result = client.audio.transcriptions.create(
#             file=("test.wav", f.read()),
#             model="whisper-large-v3-turbo",
#         )

#     text = result.text.strip()
#     print("You said:", text)

#     if len(text.strip(" .!?")) < 2:
#         continue

#     if text.lower().strip(" .!") in ["quit", "exit", "bye", "goodbye"]:
#         speak("Goodbye")
#         break

#     messages.append({"role": "user", "content": text})

#     response = client.chat.completions.create(
#         model="qwen/qwen3.8-27b",
#         messages=messages,
#     )
#     reply = response.choices[0].message.content.strip()

#     if reply:
#         print(f"Chatbot: {reply}")
#         messages.append({"role": "assistant", "content": reply})
#         save_history(messages)
#         speak(reply)


from location_tool import find_place
import json
import os
import numpy as np
from dotenv import load_dotenv
from groq import Groq
import pyttsx3
from scipy.io.wavfile import write
import sounddevice as sd

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
HISTORY_FILE = "history.json"


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


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.say(text)
    engine.runAndWait()




def record_until_silence(fs=16000, threshold=30, silence_seconds=3, max_seconds=30):
    chunk = int(0.1 * fs)
    frames = []
    silent_blocks = 0
    loud_blocks = 0
    started = False
    with sd.InputStream(samplerate=fs, channels=1, dtype="int16", blocksize=chunk) as stream:
        for _ in range(max_seconds * 10):
            data, _ = stream.read(chunk)
            frames.append(data)
            if np.abs(data).mean() > threshold:
                started = True
                loud_blocks += 1
                silent_blocks = 0
            elif started:
                silent_blocks += 1
                if silent_blocks >= silence_seconds * 10:
                    break
    if loud_blocks < 5:  # less than 0.5 s of sound: not speech
        return None
    return np.concatenate(frames)


messages = load_history()
fs = 16000

tools = [{
    "type": "function",
    "function": {
        "name": "find_place",
        "description": "Find places or addresses on a map.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "e.g. 'pharmacy near Via Toledo, Naples'"}
            },
            "required": ["query"],
        },
    },
}]

while True:
    print("Speak now...")
    audio = record_until_silence(fs)
    if audio is None:
        continue
    write("test.wav", fs, audio)

    with open("test.wav", "rb") as f:
        result = client.audio.transcriptions.create(
            file=("test.wav", f.read()),
            model="whisper-large-v3-turbo",
        )

    text = result.text.strip()
    print("You said:", text)

    if len(text.strip(" .!?")) < 2:
        continue

    if text.lower().strip(" .!") in ["quit", "exit", "bye", "goodbye"]:
        speak("Goodbye")
        break

    messages.append({"role": "user", "content": text})

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
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            places = find_place(args["query"])
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(places, ensure_ascii=False),
            })

    reply = (msg.content or "").strip()

    if reply:
        print(f"Chatbot: {reply}")
        messages.append({"role": "assistant", "content": reply})
        save_history(messages)
        speak(reply)

        