"""
Library Page

Browse all notes and their versions.
"""

import streamlit as st
from pathlib import Path
from ui.api_client import APIClient
from config import KB_DIR


def render():
    """Render the Library page"""

    st.title("📚 Library")
    st.markdown("Browse all generated notes and versions")

    # Initialize API client
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    client = APIClient(api_url)

    # Check API health
    if not client.health_check():
        st.error(
            f"⚠️ Cannot connect to API at {api_url}. "
            "Please ensure the FastAPI server is running."
        )
        return

    # Get all saved files from KB directory
    kb_path = Path(KB_DIR)

    if not kb_path.exists():
        st.info("📁 Knowledge Base directory is empty. Save some notes from the Workspace!")
        return

    # List all .md files
    md_files = sorted(kb_path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not md_files:
        st.info("📄 No markdown files found in Knowledge Base. Save some notes from the Workspace!")
        return

    # Display statistics
    st.metric("Total Notes", len(md_files))

    st.markdown("---")

    # Search/filter
    search_term = st.text_input("🔍 Search notes", placeholder="Search by filename or content...")

    # Display notes
    for md_file in md_files:
        # Apply search filter
        if search_term and search_term.lower() not in md_file.name.lower():
            continue

        with st.expander(f"📄 {md_file.name}", expanded=False):
            # Read file content
            try:
                content = md_file.read_text(encoding="utf-8")

                # Display metadata
                stat = md_file.stat()
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.caption(f"📅 Modified: {stat.st_mtime}")

                with col2:
                    st.caption(f"📏 Size: {stat.st_size} bytes")

                with col3:
                    st.caption(f"📂 Path: `{md_file}`")

                # Display content preview
                st.markdown("**Content:**")
                st.markdown(content)

                # Actions
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("📋 Copy to Clipboard", key=f"copy_{md_file.name}"):
                        # Note: Streamlit doesn't have direct clipboard access
                        # This would need JavaScript or user to manually copy
                        st.code(content, language="markdown")
                        st.info("👆 Select and copy the text above")

                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{md_file.name}"):
                        try:
                            md_file.unlink()
                            st.success(f"Deleted {md_file.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting file: {str(e)}")

                with col3:
                    # Download button
                    st.download_button(
                        label="⬇️ Download",
                        data=content,
                        file_name=md_file.name,
                        mime="text/markdown",
                        key=f"download_{md_file.name}"
                    )

            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    # Bulk operations
    if md_files:
        st.markdown("---")
        st.subheader("Bulk Operations")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📦 Export All as ZIP"):
                st.info("💡 Feature coming soon: Export all notes as a ZIP archive")

        with col2:
            if st.button("🗑️ Delete All", type="secondary"):
                if st.session_state.get("confirm_delete_all"):
                    try:
                        for md_file in md_files:
                            md_file.unlink()
                        st.success(f"Deleted {len(md_files)} files")
                        st.session_state.confirm_delete_all = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting files: {str(e)}")
                else:
                    st.session_state.confirm_delete_all = True
                    st.warning("⚠️ Click again to confirm deletion of all files")
