"""
WebScribe Streamlit UI

Main application entry point with sidebar navigation.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

# Page imports
from ui.pages import workspace, library, templates


# Page configuration
st.set_page_config(
    page_title="WebScribe",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("📝 WebScribe")
st.sidebar.markdown("Convert web pages into structured Markdown notes")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Navigation",
    options=["🔍 Workspace", "📚 Library", "⚙️ Templates"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown(
    """
    WebScribe scrapes web content, removes noise,
    and uses AI to generate clean, structured notes
    for your knowledge base.
    """
)

# API configuration in sidebar
with st.sidebar.expander("⚙️ API Configuration", expanded=False):
    api_base_url = st.text_input(
        "API Base URL",
        value="http://localhost:8000",
        key="api_base_url"
    )

    # Store in session state
    st.session_state.api_url = api_base_url

# Render selected page
if page == "🔍 Workspace":
    workspace.render()
elif page == "📚 Library":
    library.render()
elif page == "⚙️ Templates":
    templates.render()
