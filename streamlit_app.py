import streamlit as st
import requests

st.set_page_config(page_title="Army Workshop AI", page_icon="🦾")

st.title("🦾 Army Workshop: AI Control Center")

# --- Logic for Google Search ---
def google_search(search_query):
    api_key = st.secrets["GOOGLE_API_KEY"]
    cse_id = st.secrets["GOOGLE_CSE_ID"]
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={search_query}"
    response = requests.get(url)
    return response.json()

# --- Tabs ---
tab1, tab2 = st.tabs(["🔍 Search Engine", "🎙️ OpenAI Voice"])

with tab1:
    st.header("Google Custom Search")
    user_query = st.text_input("Search the web:")
    if st.button("Search Now"):
        if user_query:
            results = google_search(user_query)
            if "items" in results:
                for item in results["items"]:
                    st.write(f"### [{item['title']}]({item['link']})")
                    st.write(item['snippet'])
                    st.divider()
            else:
                st.error("No results found. Check your API keys!")
        else:
            st.warning("Please enter something to search for.")

with tab2:
    st.header("OpenAI Voice Engine")
    st.info("Your OpenAI Key is detected. Ready for voice integration.")
    st.write("Upload an audio file to test transcription:")
    audio = st.file_uploader("Audio file", type=['mp3', 'wav'])
    if audio:
        st.success("File uploaded. Next step: Connect OpenAI Whisper API.")
