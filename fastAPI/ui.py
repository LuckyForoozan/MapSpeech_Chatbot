import io
import os
import requests
import streamlit as st
from gtts import gTTS

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Voice City Assistant", page_icon="🎙️")
st.title("🎙️ Voice City Assistant")
st.caption("Ask for places in any city (e.g. *'List 5 pharmacies in Naples'*, *'Where are 5 bars in Rome?'*)")

if "chat" not in st.session_state:
    st.session_state.chat = []


def make_speech(text):
    buf = io.BytesIO()
    gTTS(text=text, lang="en").write_to_fp(buf)
    return buf.getvalue()


audio = st.audio_input("Record your question")

if audio is not None and st.session_state.get("last_id") != audio.file_id:
    st.session_state.last_id = audio.file_id

    # 1. Transcribe voice
    with st.spinner("Transcribing..."):
        r = requests.post(
            f"{API_URL}/transcribe",
            files={"file": ("input.wav", audio.getvalue(), "audio/wav")},
        )
        text = r.json().get("text", "").strip()

    if len(text.strip(" .!?")) >= 2:
        st.session_state.chat.append(("user", text))

        # 2. Query chat endpoint
        with st.spinner("Finding 5 places..."):
            r = requests.post(f"{API_URL}/chat", json={"message": text})
            reply = r.json().get("reply", "")

        st.session_state.chat.append(("assistant", reply))
        st.session_state.speech = make_speech(reply)

# Render conversation
for role, content in st.session_state.chat:
    st.chat_message(role).write(content)

# Play speech output
speech = st.session_state.pop("speech", None)
if speech:
    st.audio(speech, format="audio/mp3", autoplay=True)
