"""
Workspace Page

Submit URLs, monitor job progress, and edit notes.
"""

import time
import streamlit as st
from ui.api_client import APIClient


def render():
    """Render the Workspace page"""

    st.title("🔍 Workspace")
    st.markdown("Submit URLs and monitor processing progress")

    # Initialize API client
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    client = APIClient(api_url)

    # Check API health
    if not client.health_check():
        st.error(
            f"⚠️ Cannot connect to API at {api_url}. "
            "Please ensure the FastAPI server is running (`python main.py`)"
        )
        return

    # Section 1: Submit URLs
    st.header("Submit URLs")

    with st.form("submit_urls_form"):
        urls_input = st.text_area(
            "URLs (one per line)",
            placeholder="https://example.com\nhttps://another-site.com",
            height=100
        )

        col1, col2 = st.columns(2)

        with col1:
            engine = st.selectbox(
                "Scraper Engine",
                options=["static", "dynamic"],
                help="Static: Fast, for simple pages. Dynamic: Slower, handles JavaScript."
            )

        with col2:
            template_id = st.selectbox(
                "AI Template",
                options=["research-summary", "beginner-explainer", "api-endpoint-extractor"],
                help="Template for structuring the AI-generated note"
            )

        submit_button = st.form_submit_button("🚀 Submit", use_container_width=True)

    # Handle submission
    if submit_button:
        urls = [url.strip() for url in urls_input.split("\n") if url.strip()]

        if not urls:
            st.warning("⚠️ Please enter at least one URL")
        else:
            try:
                with st.spinner("Submitting jobs..."):
                    result = client.scrape_urls(urls, engine, template_id)

                st.success(f"✅ Submitted {len(result['jobs'])} job(s)")

                # Store the first job ID in session state for monitoring
                if result["jobs"]:
                    st.session_state.active_job_id = result["jobs"][0]["job_id"]
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Error submitting URLs: {str(e)}")

    # Section 2: Monitor Active Job
    st.markdown("---")
    st.header("Active Job")

    active_job_id = st.session_state.get("active_job_id")

    if not active_job_id:
        st.info("💡 No active job. Submit URLs above to get started.")
        return

    # Fetch job status
    try:
        job = client.get_job_status(active_job_id)

        # Display job info
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Status", job["status"].upper())

        with col2:
            st.metric("URL", job["url"][:40] + "..." if len(job["url"]) > 40 else job["url"])

        with col3:
            st.metric("Engine", job["engine"].upper())

        # Display logs
        with st.expander("📋 Job Logs", expanded=True):
            for log in job["logs"]:
                if "ERROR" in log:
                    st.error(log)
                elif "SUCCESS" in log or "completed" in log.lower():
                    st.success(log)
                else:
                    st.text(log)

        # Auto-refresh while job is running
        if job["status"] in ["queued", "running"]:
            st.info("⏳ Job is processing... Auto-refreshing every 3 seconds.")
            time.sleep(3)
            st.rerun()

        # If job is done, show the note
        elif job["status"] == "done":
            st.success("✅ Job completed successfully!")

            # Fetch notes
            try:
                notes = client.get_notes_for_job(active_job_id)

                if notes:
                    _render_note_editor(client, notes[0])
                else:
                    st.warning("No notes found for this job.")

            except Exception as e:
                st.error(f"Error fetching notes: {str(e)}")

        # If job failed, show error
        elif job["status"] == "failed":
            st.error("❌ Job failed. Check the logs above for details.")

            # Clear button
            if st.button("🔄 Clear Failed Job"):
                del st.session_state.active_job_id
                st.rerun()

    except Exception as e:
        st.error(f"Error fetching job status: {str(e)}")


def _render_note_editor(client: APIClient, note: dict):
    """Render the note editor section"""

    st.markdown("---")
    st.header("📝 Generated Note")

    # Display note metadata
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Version", f"v{note['version']}")

    with col2:
        st.metric("Template", note["template_id"])

    with col3:
        if note.get("saved_path"):
            st.success("💾 Saved")
        else:
            st.info("📄 Not saved")

    # Editable title
    edited_title = st.text_input(
        "Title",
        value=note["title"],
        key=f"note_title_{note['id']}"
    )

    # Editable content
    edited_content = st.text_area(
        "Content (Markdown)",
        value=note["content"],
        height=400,
        key=f"note_content_{note['id']}"
    )

    # Display tags
    if note.get("tags"):
        st.markdown("**Tags:** " + ", ".join([f"`{tag}`" for tag in note["tags"]]))

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Save Changes", use_container_width=True):
            try:
                with st.spinner("Saving..."):
                    client.update_note(
                        note["id"],
                        title=edited_title if edited_title != note["title"] else None,
                        content=edited_content if edited_content != note["content"] else None
                    )
                st.success("✅ Note updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating note: {str(e)}")

    with col2:
        if st.button("📁 Save to Knowledge Base", use_container_width=True):
            try:
                with st.spinner("Saving to Knowledge Base..."):
                    result = client.save_note_to_kb(note["id"])
                st.success(f"✅ Saved to: `{result['saved_path']}`")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving to KB: {str(e)}")

    with col3:
        with st.popover("🔄 Re-run AI"):
            st.markdown("**Re-run with different template:**")
            new_template = st.selectbox(
                "Template",
                options=["research-summary", "beginner-explainer", "api-endpoint-extractor"],
                key=f"rerun_template_{note['id']}"
            )

            if st.button("▶️ Re-run", key=f"rerun_btn_{note['id']}"):
                try:
                    with st.spinner("Re-running AI synthesis..."):
                        client.rerun_ai_synthesis(note["job_id"], new_template)
                    st.success("✅ Re-run started! Check Library for new version.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error re-running: {str(e)}")

    # Preview rendered markdown
    with st.expander("👁️ Preview Rendered Markdown"):
        st.markdown(edited_content)
