import streamlit as st

st.title("🔧 System Diagnostics")

# This checks if the "Keys" exist in your Secrets vault
st.subheader("Secrets Check")

keys_to_check = ["GOOGLE_API_KEY", "GOOGLE_CSE_ID", "OPENAI_API_KEY"]

for key in keys_to_check:
    if key in st.secrets:
        st.success(f"✅ {key} is found in Secrets.")
    else:
        st.error(f"❌ {key} is MISSING from Secrets.")

st.divider()

# This checks if the necessary libraries are installed
st.subheader("Library Check")
try:
    import requests
    st.success("✅ 'requests' library is ready.")
except:
    st.error("❌ 'requests' library is missing from requirements.txt")

st.info("Once all three keys show a green checkmark above, your search engine will work.")
