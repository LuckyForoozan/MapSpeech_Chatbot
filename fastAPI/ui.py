import io
import requests
import streamlit as st
from gtts import gTTS
import os

# API_URL = "http://127.0.0.1:8000"
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.title("Voice Chatbot")

if "chat" not in st.session_state:
    st.session_state.chat = []


def make_speech(text):
    buf = io.BytesIO()
    gTTS(text).write_to_fp(buf)
    return buf.getvalue()


audio = st.audio_input("Record your message")

if audio is not None and st.session_state.get("last_id") != audio.file_id:
    st.session_state.last_id = audio.file_id

    r = requests.post(
        f"{API_URL}/transcribe",
        files={"file": ("input.wav", audio.getvalue(), "audio/wav")},
    )
    text = r.json()["text"]

    if len(text.strip(" .!?")) >= 2:
        st.session_state.chat.append(("user", text))
        r = requests.post(f"{API_URL}/chat", json={"message": text})
        reply = r.json()["reply"]
        st.session_state.chat.append(("assistant", reply))
        st.session_state.speech = make_speech(reply)

for role, content in st.session_state.chat:
    st.chat_message(role).write(content)

speech = st.session_state.pop("speech", None)
if speech:
    st.audio(speech, format="audio/mp3", autoplay=True)