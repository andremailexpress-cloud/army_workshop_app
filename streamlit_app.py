import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Army Workshop AI", page_icon="🦾", layout="wide")

st.title("🦾 Army Workshop: AI Control Center")
st.markdown("---")

# 2. Inventory Check (Taking Stock)
st.subheader("System Status")
col1, col2, col3 = st.columns(3)
col1.metric("App Link", "Active ✅")
col2.metric("GitHub Sync", "Connected ✅")
col3.metric("Environment", "Ready 🚀")

st.divider()

# 3. Custom Workshop Tools
st.header("Custom Workshop Tools")

tab1, tab2 = st.tabs(["🔍 Google Search Engine", "🎙️ OpenAI Voice Command"])

with tab1:
    st.write("### Google Custom Search")
    query = st.text_input("Enter search term:", placeholder="What are we looking for?")
    if st.button("Search Now"):
        # We will plug your specific Google API logic here next
        st.info(f"Handshaking with Google Search Engine for: {query}...")
        st.warning("Note: Ensure your GOOGLE_API_KEY is in Streamlit Secrets.")

with tab2:
    st.write("### OpenAI Voice & Audio")
    st.info("This section will use your OpenAI API key for voice processing.")
    audio_file = st.file_uploader("Upload an audio file to transcribe", type=['mp3', 'wav', 'm4a'])
    if audio_file:
        st.success("Audio received! Ready for OpenAI transcription.")

st.sidebar.title("Workshop Settings")
st.sidebar.write("Using API keys for:")
st.sidebar.checkbox("OpenAI", value=True, disabled=True)
st.sidebar.checkbox("Google Search", value=True, disabled=True)
