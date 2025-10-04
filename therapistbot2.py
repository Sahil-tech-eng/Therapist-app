import streamlit as st
import pandas as pd
import plotly.express as px
from deep_translator import GoogleTranslator
from langdetect import detect
import json, uuid
from datetime import datetime
import random
import sqlite3


# --- SQLite DB ---
DB_FILE = "therapist_chatbot.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    user_id TEXT PRIMARY KEY,
    history TEXT,
    moods TEXT,
    last_active TIMESTAMP,
    growth_plan TEXT
)
""")
conn.commit()

# --- Session state ---
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())
if "history" not in st.session_state: st.session_state.history = []
if "moods" not in st.session_state: st.session_state.moods = []
if "therapist_mode" not in st.session_state: st.session_state.therapist_mode = None
if "quote" not in st.session_state: st.session_state.quote = None
if "growth_plan" not in st.session_state: st.session_state.growth_plan = None

# --- Mobile CSS ---
st.set_page_config(page_title="Therapist Chatbot", page_icon="🛋️", layout="wide")
st.markdown("""
<style>
input[type="text"] { width: 100% !important; padding: 10px !important; font-size:16px !important; }
.stMarkdown p { margin:0 0 5px 0; }
[data-testid="stVerticalBlock"] > div:nth-child(1) { max-height:60vh; overflow-y:auto; }
button[role="button"] { font-size:16px; padding:12px; }
@media (max-width:768px){ .css-18e3th9 { padding:1rem; } }
</style>
""", unsafe_allow_html=True)

# --- DB functions ---
def load_session():
    c.execute("SELECT history, moods, growth_plan FROM sessions WHERE user_id=?", (st.session_state.user_id,))
    row = c.fetchone()
    if row:
        st.session_state.history = json.loads(row[0])
        st.session_state.moods = json.loads(row[1])
        st.session_state.growth_plan = json.loads(row[2]) if row[2] else None

def save_session():
    c.execute("""
    INSERT INTO sessions (user_id, history, moods, last_active, growth_plan)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    history=excluded.history,
    moods=excluded.moods,
    last_active=excluded.last_active,
    growth_plan=excluded.growth_plan
    """, (st.session_state.user_id,
          json.dumps(st.session_state.history),
          json.dumps(st.session_state.moods),
          datetime.now(),
          json.dumps(st.session_state.growth_plan) if st.session_state.growth_plan else None))
    conn.commit()

# --- Core functions ---
def generate_quote():
    quotes = [
        "Breathe. This moment is yours. 💙",
        "Small steps every day create big change.",
        "You are stronger than you think.",
        "Every emotion is valid. Feel it and move forward.",
        "Take a deep breath, the world is patient with you."
    ]
    return random.choice(quotes)

def detect_language(text):
    try: return detect(text)
    except: return "en"

def translate_text(text, target_lang="en"):
    try: return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except: return text

def choose_emoji(text):
    sad_words = ["sad","depressed","lonely","anxious","tired","unhappy"]
    happy_words = ["happy","good","great","excited","joyful"]
    if any(word in text.lower() for word in sad_words):
        st.session_state.moods.append({"time": datetime.now().isoformat(),"mood":"sad"})
        return "💙😔"
    elif any(word in text.lower() for word in happy_words):
        st.session_state.moods.append({"time": datetime.now().isoformat(),"mood":"happy"})
        return "😄🎉"
    else:
        st.session_state.moods.append({"time": datetime.now().isoformat(),"mood":"neutral"})
        return "🙂"

def crisis_check(text):
    crisis_words = ["suicide","worthless","can’t live","die","kill myself"]
    return any(word in text.lower() for word in crisis_words)

def generate_bot_response(user_input, mode="Friendly Friend"):
    # Crisis handling
    if crisis_check(user_input):
        return ("I hear your pain. You are not alone. "
                "If you are in India, call Vandrevala Helpline: 1860 266 2345 💙")
    
    # Canned responses
    friendly_responses = [
        "Tell me more about that 🙂",
        "I understand. How does that make you feel?",
        "That's interesting. Can you elaborate?",
        "Thanks for sharing. I’m here for you."
    ]
    mentor_responses = [
        "Remember, every challenge is a lesson. 💡",
        "Wisdom comes from patience and reflection.",
        "Stay calm. Reflect and act mindfully.",
        "Small progress is still progress."
    ]
    professional_responses = [
        "I understand. Can you describe how that affects your daily life?",
        "It sounds like you're going through a difficult time.",
        "Let's explore those feelings together.",
        "Your emotions are valid. Thank you for sharing."
    ]
    
    responses = {
        "Wise Mentor 🧘": mentor_responses,
        "Friendly Friend 😄": friendly_responses,
        "Professional Therapist 🩺": professional_responses
    }
    return random.choice(responses.get(mode, friendly_responses))

def display_chat():
    for msg in st.session_state.history:
        if msg["role"]=="user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Bot:** {msg['content']} {choose_emoji(msg['content'])}")

def handle_input():
    user_input = st.session_state.user_input
    if not user_input.strip(): return
    lang = detect_language(user_input)
    translated_input = translate_text(user_input, target_lang="en")
    st.session_state.history.append({"role":"user","content":user_input})

    bot_reply_en = generate_bot_response(translated_input, st.session_state.therapist_mode)
    bot_reply_final = translate_text(bot_reply_en, target_lang=lang)
    st.session_state.history.append({"role":"bot","content":bot_reply_final})

    st.session_state.user_input=""
    update_growth_plan()
    save_session()

def generate_session_summary():
    if not st.session_state.history: 
        st.warning("No conversation to summarize yet."); return
    st.success("Session Summary:")
    st.markdown(f"> You shared your feelings. The chatbot responded empathetically and encouraged positive reflection.")

def update_growth_plan():
    user_texts = [m['content'] for m in st.session_state.history if m['role']=="user"]
    if len(user_texts)%5==0 and user_texts:
        st.session_state.growth_plan = "💡 Try journaling daily for 5 minutes and reflect on positive moments."

def show_growth_plan():
    if st.session_state.growth_plan:
        st.info(f"💡 Personalized Growth Plan:\n{st.session_state.growth_plan}")

# --- Streamlit UI ---
st.title("🛋️ Therapist-Friend Chatbot")
st.subheader("Your personal AI therapy buddy")

if st.session_state.therapist_mode is None:
    st.session_state.therapist_mode = st.radio(
        "Choose a mode:",
        ["Wise Mentor 🧘","Friendly Friend 😄","Professional Therapist 🩺"]
    )

if st.session_state.quote is None: st.session_state.quote = generate_quote()
st.markdown(f"> {st.session_state.quote}")

load_session()
st.divider()
display_chat()
show_growth_plan()

st.text_input("Type your message here...", key="user_input", on_change=handle_input, placeholder="Start typing...")

if st.button("📝 Generate Session Summary"): generate_session_summary()

if st.session_state.moods:
    df_moods = pd.DataFrame(st.session_state.moods)
    fig = px.line(df_moods, x="time", y=[1]*len(df_moods), color="mood",
                  markers=True, labels={"y":"Mood"}, title="Mood Over Time")
    st.plotly_chart(fig, use_container_width=True)
