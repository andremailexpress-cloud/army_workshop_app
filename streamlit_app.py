import streamlit as st
import requests

# 1. Page Setup
st.set_page_config(page_title="Army AI Workshop", page_icon="🦾")
st.title("🦾 Army AI Control Center")

# 2. The Logic (Using your 3 specific keys)
def run_search(query):
    try:
        # These names MUST match what you put in the Secrets box below
        api_key = st.secrets["GOOGLE_CLOUD_KEY"]
        search_id = st.secrets["GOOGLE_SEARCH_ID"]
        
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_id}&q={query}"
        response = requests.get(url)
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"System Error: {e}")
        return []

# 3. The Interface
tab1, tab2 = st.tabs(["🔍 Web Search", "🎙️ OpenAI Voice"])

with tab1:
    search_query = st.text_input("Enter your search:")
    if st.button("Run Search"):
        if search_query:
            results = run_search(search_query)
            for item in results:
                st.markdown(f"### [{item['title']}]({item['link']})")
                st.write(item['snippet'])
                st.divider()

with tab2:
    st.header("OpenAI Integration")
    if "OPENAI_KEY" in st.secrets:
        st.success("✅ OpenAI Key is active.")
        st.write("Ready to process voice/audio commands.")
    else:
        st.error("❌ OpenAI Key not found in Secrets.")
