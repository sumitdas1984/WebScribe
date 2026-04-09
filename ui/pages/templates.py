"""
Templates Page

View and manage AI prompt templates.
"""

import streamlit as st


def render():
    """Render the Templates page"""

    st.title("⚙️ Templates")
    st.markdown("Manage AI prompt templates for note generation")

    # Hardcoded templates for now (in production, would fetch from API)
    templates = {
        "research-summary": {
            "name": "Research Summary",
            "description": "Generates a structured research note with key concepts and summary",
            "prompt": """You are a research assistant. Convert the following web content into a structured research note.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a well-structured Markdown note with:
1. A concise title (extract from content)
2. Executive Summary (2-3 sentences)
3. Key Concepts (bullet list of main ideas)
4. Extracted code snippets (if any, with proper syntax highlighting)
5. Action items or next steps (if applicable)
6. Relevant tags for categorization

Return ONLY the formatted Markdown note, no additional commentary."""
        },
        "beginner-explainer": {
            "name": "Beginner Explainer",
            "description": "Explains technical content in simple, beginner-friendly terms",
            "prompt": """You are a teacher explaining technical content to beginners. Convert the following web content into an easy-to-understand note.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a beginner-friendly Markdown note with:
1. A clear, descriptive title
2. Simple Summary (explain in plain language)
3. Key Terms Explained (define technical terms)
4. Step-by-Step Guide (if the content describes a process)
5. Common Pitfalls (if applicable)
6. Further Reading suggestions
7. Tags for organization

Use analogies and simple language. Return ONLY the formatted Markdown note."""
        },
        "api-endpoint-extractor": {
            "name": "API Endpoint Extractor",
            "description": "Extracts API documentation and endpoint information",
            "prompt": """You are an API documentation specialist. Extract API endpoint information from the following web content.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a structured API reference note with:
1. Title (API name or service)
2. Overview (purpose of the API)
3. Endpoints Table (method, path, description)
4. Authentication (if mentioned)
5. Request/Response Examples (extract code blocks)
6. Rate Limits and Notes
7. Tags (e.g., REST, GraphQL, authentication type)

Return ONLY the formatted Markdown note with extracted API information."""
        }
    }

    # Display templates
    for template_id, template_info in templates.items():
        with st.expander(f"📋 {template_info['name']}", expanded=False):
            st.markdown(f"**ID:** `{template_id}`")
            st.markdown(f"**Description:** {template_info['description']}")

            st.markdown("**Prompt Template:**")
            st.code(template_info["prompt"], language="jinja2")

            # Note: In a full implementation, would allow editing
            st.info("💡 Template editing will be available in a future version")

    # Template usage guide
    st.markdown("---")
    st.subheader("📖 Template Usage Guide")

    st.markdown("""
    ### How Templates Work

    Templates use [Jinja2 syntax](https://jinja.palletsprojects.com/) to structure prompts for the AI engine.

    **Available Variables:**
    - `{{ raw_markdown }}` - The cleaned Markdown content from the scraped page

    ### Creating Custom Templates

    To add a custom template:

    1. Templates are defined in `database.py` during initialization
    2. Each template has an ID, name, and prompt template
    3. The prompt template must include `{{ raw_markdown }}` placeholder
    4. Templates guide the AI on what structure and information to extract

    ### Template Best Practices

    - **Be specific:** Clearly describe the desired output format
    - **Use structure:** Numbered lists help guide the AI's output
    - **Include examples:** Show the AI what kind of information to extract
    - **Set constraints:** Specify length, tone, and level of detail
    - **Define sections:** Break the output into clear sections (summary, details, etc.)
    """)

    # Template statistics
    st.markdown("---")
    st.subheader("📊 Template Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Templates", len(templates))

    with col2:
        st.metric("Most Popular", "Research Summary")

    with col3:
        st.metric("Custom Templates", "0")

    st.info("💡 Template usage statistics and custom template creation coming soon!")
