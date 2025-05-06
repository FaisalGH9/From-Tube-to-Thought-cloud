import streamlit as st
st.set_page_config(
    page_title="YouTube AI Assistant C-Version",
    page_icon="🎬",
    layout="wide"
)

import asyncio
import time
import datetime
import base64
from core.engine import ProcessingEngine

engine = ProcessingEngine()

# Session defaults
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'processing_time' not in st.session_state:
    st.session_state.processing_time = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'options' not in st.session_state:
    st.session_state.options = {}

def get_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")

# Sidebar UI
with st.sidebar:
    st.markdown("### ⚙️ Video Duration")
    duration = st.selectbox("", [
        "Full video", "First 5 minutes", "First 10 minutes",
        "First 30 minutes", "First 60 minutes"
    ])

    turbo = st.toggle("🚀 Turbo Mode", value=False, help="Turn on for long videos (> 45 mins) for faster results.")
    st.caption("💡 If you're not in a rush, keep it off to save developer costs 😊.")

    st.button("Apply Settings")

    st.markdown("---")
    st.markdown("### About This App")
    st.markdown("""
**From Tube To Thought** turns YouTube videos into something you can **chat with and understand instantly** — no need to watch the whole thing.

🌟 **Important:** This assistant can only understand what was said out loud in the video. Visuals/text on screen will not be processed.

If you're asking about text on the screen, visuals, or actions, it won’t work — it’s not psychic… just very good at listening.
    """)

    st.markdown("---")
    st.markdown("### Connect")
    st.markdown("""
    <a href="https://github.com/FaisalGH9" target="_blank">
        <img src="https://img.shields.io/badge/GitHub-FaisalGH9-black?logo=github" alt="GitHub Badge">
    </a>
    """, unsafe_allow_html=True)

# --- MAIN SECTION UI ---
st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)

# Centered logo
with open("logo.png", "rb") as f:
    logo_bytes = f.read()
logo_base64 = base64.b64encode(logo_bytes).decode()
st.markdown(f"<img src='data:image/png;base64,{logo_base64}' style='width:280px;margin-bottom:10px;'/>", unsafe_allow_html=True)

# Title + subtitle
st.markdown("<h1 style='text-align:center;'>Welcome to From Tube To Thought </h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Drop in a YouTube link, and I’ll transcribe, summarize, and answer your questions.</p>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- YouTube input section ---
col_url, col_button = st.columns([6, 1])
with col_url:
    youtube_url = st.text_input("", placeholder="Paste YouTube URL here")
with col_button:
    process = st.button("Process")

# --- Process the video ---
if process and youtube_url:
    start_time = time.time()
    st.session_state.processing = True
    st.session_state.chat_history = []

    duration_map = {
        "Full video": "full_video",
        "First 5 minutes": "first_5_minutes",
        "First 10 minutes": "first_10_minutes",
        "First 30 minutes": "first_30_minutes",
        "First 60 minutes": "first_60_minutes"
    }

    options = {
        "duration": duration_map.get(duration, "full_video"),
        "turbo": turbo
    }
    st.session_state.options = options

    with st.status("Processing video...", expanded=True) as status:
        try:
            st.write("Downloading and transcribing video...")
            video_id = asyncio.run(engine.process_video(youtube_url, options))
            st.session_state.video_id = video_id

            timestamp = get_timestamp()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "I've processed the video and I'm ready to answer your questions.",
                "timestamp": timestamp
            })

            end_time = time.time()
            st.session_state.processing_time = end_time - start_time
            status.update(label="Processing complete!", state="complete")
        except Exception as e:
            st.error(f"Error processing video: {str(e)}")
            status.update(label="Processing failed", state="error")

    st.session_state.processing = False

if st.session_state.processing_time:
    st.info(f"Processing completed in {st.session_state.processing_time:.2f} seconds")

# --- Main Tabs ---
if st.session_state.video_id:
    tab1, tab2 = st.tabs(["💬 Chat with Video", "🧠 Summarize"])

    # --- Chat tab ---
    with tab1:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🧹 Clear Chat"):
                st.session_state.chat_history = [{
                    "role": "assistant",
                    "content": "I've processed the video and I'm ready to answer your questions.",
                    "timestamp": get_timestamp()
                }]
                st.rerun()

        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div style='background:#e6f7ff;padding:10px;border-radius:10px;margin-bottom:10px;text-align:right;'>"
                            f"<div style='font-size:0.8em;color:#666'>{message['timestamp']}</div><b>You:</b> {message['content']}</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background:#f0f0f0;padding:10px;border-radius:10px;margin-bottom:10px;'>"
                            f"<div style='font-size:0.8em;color:#666'>{message['timestamp']}</div><b>Assistant:</b> {message['content']}</div>",
                            unsafe_allow_html=True)

        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                user_query = st.text_input("Ask something about the video:")
            with col2:
                send_button = st.form_submit_button("Send")

        if send_button and user_query:
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_query,
                "timestamp": get_timestamp()
            })
            st.rerun()

        if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
            last_user_query = st.session_state.chat_history[-1]["content"]

            with st.status("Generating response...", expanded=False) as status:
                try:
                    start_time = time.time()
                    result = asyncio.run(engine.query_video(
                        st.session_state.video_id,
                        last_user_query,
                        stream=False,
                        options=st.session_state.options
                    ))

                    response = result["response"]

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": get_timestamp()
                    })

                    latency = time.time() - start_time
                    status.update(label=f"Response generated in {latency:.2f} seconds", state="complete")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    status.update(label="Response generation failed", state="error")

    # --- Summary tab ---
    with tab2:
        summary_length = st.radio("Summary length", ["Short", "Medium", "Detailed"], index=1, horizontal=True)
        if st.button("Generate Summary"):
            summary_container = st.empty()

            with st.status("Generating summary...", expanded=False) as status:
                try:
                    start_time = time.time()
                    summary = asyncio.run(engine.summarize_video(
                        st.session_state.video_id,
                        length=summary_length.lower()
                    ))

                    timestamp = get_timestamp()
                    summary_container.markdown(f"""
                    <div style='background:#f0f0f0;padding:15px;border-radius:10px;margin-bottom:10px;'>
                        <div style='font-size:0.8em;color:#666;margin-bottom:5px;'>{timestamp}</div>
                        <h3>Video Summary ({summary_length})</h3>
                        {summary}
                    </div>
                    """, unsafe_allow_html=True)

                    latency = time.time() - start_time
                    status.update(label=f"Summary generated in {latency:.2f} seconds", state="complete")
                except Exception as e:
                    st.error(f"Error generating summary: {str(e)}")
                    status.update(label="Summary generation failed", state="error")
