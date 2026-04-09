import streamlit as st
import time
import pandas as pd
from datetime import datetime
import markdown

# --- CONFIGURATION ---
st.set_page_config(
    page_title="WebScribe | Research Assistant",
    page_icon="✍️",
    layout="wide",
)

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e9ecef;
        background-color: white;
        margin-bottom: 1rem;
    }
    .md-preview {
        background-color: white;
        padding: 2rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        min-height: 400px;
        color: #212529;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'research_notes' not in st.session_state:
    st.session_state.research_notes = [
        {
            "id": "1",
            "url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI Documentation",
            "date": "2024-05-20",
            "content": "# FastAPI Overview\n\nFastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints.\n\n## Key Features\n- **Fast**: Very high performance.\n- **Fast to code**: Increase the speed to develop features by about 200% to 300%.\n- **Fewer bugs**: Reduce about 40% of human (developer) induced errors.",
            "tags": ["Python", "API", "Backend"]
        }
    ]

if 'processing_queue' not in st.session_state:
    st.session_state.processing_queue = []

# --- MOCK LOGIC (API CANDIDATES) ---
def mock_process_url(url):
    """Simulates the FastAPI background task for scraping and LLM processing."""
    job = {"url": url, "status": "Initializing", "progress": 0}
    st.session_state.processing_queue.append(job)
    
    # Simulate multi-stage automation
    stages = [
        ("Bypassing Paywalls & Scraping...", 0.3),
        ("Cleaning HTML to Markdown...", 0.6),
        ("LLM: Synthesizing Summary...", 0.9),
        ("Completed", 1.0)
    ]
    
    placeholder = st.empty()
    
    with st.status(f"Processing {url}", expanded=True) as status:
        for stage_text, prog in stages:
            st.write(f"⚙️ {stage_text}")
            time.sleep(0.8)
        status.update(label="Scribe processing complete!", state="complete")
    
    new_note = {
        "id": str(len(st.session_state.research_notes) + 1),
        "url": url,
        "title": "New Research Note " + datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "content": f"# Research Summary: {url}\n\n## Abstract\nThis is an AI-generated summary of the content found at the provided link.\n\n## Key Findings\n- Automation is key to research efficiency.\n- Markdown is the best format for portability.",
        "tags": ["Auto-generated"]
    }
    st.session_state.research_notes.insert(0, new_note)
    st.session_state.processing_queue = [] # Clear queue for demo

# --- UI LAYOUT ---

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("✍️ WebScribe")
        st.caption("v1.0.0 | Intelligent Research Assistant")
        st.markdown("---")
        
        menu = st.radio("Navigation", ["🔍 Workspace", "📚 Library", "⚙️ Templates"])
        
        st.markdown("---")
        st.subheader("New Task")
        url_input = st.text_input("Paste URL here:", placeholder="https://example.com/article")
        if st.button("Scribe It!", type="primary"):
            if url_input:
                mock_process_url(url_input)
            else:
                st.error("Please enter a valid URL")

    # --- MAIN CONTENT ---
    if menu == "🔍 Workspace":
        st.header("Research Workspace")
        
        if not st.session_state.research_notes:
            st.info("Your workspace is empty. Paste a URL in the sidebar to begin.")
        else:
            # Workspace view (Most recent note)
            current_note = st.session_state.research_notes[0]
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Original Metadata")
                with st.container(border=True):
                    st.write(f"**Source:** [{current_note['url']}]({current_note['url']})")
                    st.write(f"**Date Scribed:** {current_note['date']}")
                    st.write(f"**Status:** ✅ Processed")
                    st.text_input("Note Title", value=current_note['title'])
                    st.multiselect("Tags", ["Python", "Machine Learning", "Backend", "AI", "API", "Strategy"], default=current_note['tags'])
                
                st.info("💡 **Pro-Tip:** The LLM extracts code snippets and action items automatically.")

            with col2:
                st.subheader("Markdown Result")
                tab1, tab2 = st.tabs(["Editor", "Preview"])
                
                with tab1:
                    content = st.text_area("Markdown Body", value=current_note['content'], height=450)
                with tab2:
                    html_content = markdown.markdown(content)
                    st.markdown(f'<div class="md-preview">{html_content}</div>', unsafe_allow_html=True)
                
                st.button("Save Changes to Library")

    elif menu == "📚 Library":
        st.header("Knowledge Base")
        
        # Filter and Search
        search = st.text_input("🔍 Search library...", placeholder="Keywords, URLs, or tags")
        
        # Display Library as a Table/List
        for note in st.session_state.research_notes:
            with st.expander(f"{note['date']} | {note['title']}"):
                st.write(f"**URL:** {note['url']}")
                st.markdown(note['content'])
                st.button(f"Export as .md", key=note['id'])

    elif menu == "⚙️ Templates":
        st.header("Research Templates")
        st.write("Configure how WebScribe structures your research.")
        
        st.selectbox("Active Template", ["Executive Summary (Default)", "Technical Documentation", "Literature Review", "API Specification"])
        
        st.text_area("Template Structure (Markdown)", value="""# {{title}}
## Metadata
- **URL:** {{url}}
- **Tags:** {{tags}}

## Summary
{{summary}}

## Detailed Notes
{{content}}

## Code & Links
{{snippets}}""")
        st.button("Update Template")

if __name__ == "__main__":
    main()