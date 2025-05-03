import asyncio
import time
import datetime
import streamlit as st
from core.engine import ProcessingEngine

engine = ProcessingEngine()

st.set_page_config(
    page_title="YouTube AI Assistant C-Version",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 YouTube AI Assistant C-Version")
st.markdown("""
This version processes YouTube videos and allows you to ask questions 
about their content using LLM-powered retrieval.
""")

# Session state defaults
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

# Sidebar input
with st.sidebar:
    with st.form("video_form"):
        youtube_url = st.text_input("🎥 YouTube URL")

        duration = st.selectbox("⏱️ Video Duration", [
            "Full video", "First 5 minutes", "First 10 minutes",
            "First 30 minutes", "First 60 minutes"
        ])

        parallelization = st.slider("🚀 Parallel Processing", 1, 5, 3)

        with st.expander("Advanced Options"):
            search_method = st.radio("Search Method", [
                "Hybrid (Vector + Keyword)", "Vector Only", "Keyword Only"
            ], index=0)

            model_option = st.selectbox("LLM Model", [
                "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"
            ])

        submit_button = st.form_submit_button("Process Video")

    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    - Hybrid search (vector + keyword)
    - Multi-level caching
    - Streaming or full responses
    - Parallel processing
    """)

# Process video
if submit_button and youtube_url:
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

    search_method_map = {
        "Hybrid (Vector + Keyword)": "hybrid",
        "Vector Only": "vector",
        "Keyword Only": "keyword"
    }

    options = {
        "duration": duration_map.get(duration, "full_video"),
        "parallelization": parallelization,
        "search_method": search_method_map.get(search_method, "hybrid"),
        "model": model_option
    }
    st.session_state.options = options  # ✅ save for later use

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

# Main interaction UI
if st.session_state.video_id:
    tab1, tab2 = st.tabs(["Chat About Video", "Summarize"])

    # Chat tab
    with tab1:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("Clear Chat"):
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

                    options = st.session_state.get("options", {})  # ✅ load saved options
                    result = asyncio.run(engine.query_video(
                        st.session_state.video_id,
                        last_user_query,
                        stream=False,
                        options=options
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

    # Summary tab
    with tab2:
        summary_length = st.radio("Summary Length", ["Short", "Medium", "Detailed"], index=1, horizontal=True)
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
