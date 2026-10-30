import io
import os
import requests
import streamlit as st
from gtts import gTTS
from streamlit_js_eval import get_geolocation

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Voice Chatbot", page_icon="🎙️")
st.title("🎙️ Voice Chatbot")

# Attempt to detect live browser geolocation
loc = get_geolocation()
if loc and "coords" in loc:
    st.session_state["user_lat"] = loc["coords"]["latitude"]
    st.session_state["user_lon"] = loc["coords"]["longitude"]

user_lat = st.session_state.get("user_lat")
user_lon = st.session_state.get("user_lon")

if user_lat is not None and user_lon is not None:
    st.success(f"📍 Location detected: ({user_lat:.4f}, {user_lon:.4f})")
else:
    st.info("📍 Waiting for location access... Please allow location in your browser to find nearest places.")

if "chat" not in st.session_state:
    st.session_state.chat = []


def make_speech(text):
    buf = io.BytesIO()
    gTTS(text=text, lang="en").write_to_fp(buf)
    return buf.getvalue()


audio = st.audio_input("Record your message")

if audio is not None and st.session_state.get("last_id") != audio.file_id:
    st.session_state.last_id = audio.file_id

    # 1. Transcribe audio to text
    with st.spinner("Transcribing..."):
        r = requests.post(
            f"{API_URL}/transcribe",
            files={"file": ("input.wav", audio.getvalue(), "audio/wav")},
        )
        text = r.json().get("text", "").strip()

    if len(text.strip(" .!?")) >= 2:
        st.session_state.chat.append(("user", text))

        # 2. Send text + user GPS coordinates to chat API
        payload = {"message": text}
        if user_lat is not None and user_lon is not None:
            payload["latitude"] = float(user_lat)
            payload["longitude"] = float(user_lon)

        with st.spinner("Thinking & finding places..."):
            r = requests.post(f"{API_URL}/chat", json=payload)
            reply = r.json().get("reply", "")

        st.session_state.chat.append(("assistant", reply))
        st.session_state.speech = make_speech(reply)

# Display chat history
for role, content in st.session_state.chat:
    st.chat_message(role).write(content)

# Autoplay synthesized speech
speech = st.session_state.pop("speech", None)
if speech:
    st.audio(speech, format="audio/mp3", autoplay=True)
