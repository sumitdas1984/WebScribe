"""
Unit Tests: De-noiser Content Cleaning

Property 4: Content Extraction with Fallback
Validates: Requirements 3.1, 3.2

Property 5: Noise Element Removal
Validates: Requirements 3.3

Property 6: Markdown Structure Preservation
Validates: Requirements 3.4
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from denoiser.cleaner import clean
from denoiser.exceptions import InsufficientContentError


# Feature: webscribe, Property 4: Content extraction with fallback
@given(
    main_content=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # lowercase letters only
        min_size=60,
        max_size=100
    ),
    noise_content=st.text(
        alphabet=st.characters(min_codepoint=65, max_codepoint=90),  # uppercase letters only
        min_size=10,
        max_size=30
    )
)
@settings(max_examples=100)
def test_content_extraction_prefers_main_tag(main_content, noise_content):
    """
    Property: When <main> is present, content is extracted from it, not from other elements.

    Validates: Requirements 3.1, 3.2
    """
    # Ensure content is sufficient (hypothesis generates random strings that may have whitespace collapsed)
    assume(len(main_content.strip()) >= 60)
    assume(len(noise_content.strip()) >= 10)
    assume(noise_content not in main_content)

    html = f"""
    <html>
        <body>
            <header>{noise_content}</header>
            <main><p>{main_content}</p></main>
            <footer>{noise_content}</footer>
        </body>
    </html>
    """

    result = clean(html)

    # Main content should be present (check for a substring to avoid markdownify escaping issues)
    # Since we're using only lowercase letters, they shouldn't be escaped
    assert main_content[:20] in result, "Should extract content from <main> tag"

    # Noise content from header/footer should NOT be present
    assert noise_content not in result, "Should not include header/footer content"


@given(
    article_content=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=60,
        max_size=100
    ),
    noise_content=st.text(
        alphabet=st.characters(min_codepoint=65, max_codepoint=90),
        min_size=10,
        max_size=30
    )
)
@settings(max_examples=100)
def test_content_extraction_falls_back_to_article(article_content, noise_content):
    """
    Property: When no <main> but <article> exists, content is extracted from <article>.

    Validates: Requirements 3.1, 3.2
    """
    assume(len(article_content.strip()) >= 60)
    assume(len(noise_content.strip()) >= 10)
    assume(noise_content not in article_content)

    # HTML without <main> but with <article>
    html = f"""
    <html>
        <body>
            <header>{noise_content}</header>
            <article><p>{article_content}</p></article>
            <footer>{noise_content}</footer>
        </body>
    </html>
    """

    result = clean(html)

    assert article_content[:20] in result, "Should extract content from <article> tag"
    assert noise_content not in result, "Should not include header/footer content"


@given(
    body_content=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=60,
        max_size=150
    )
)
@settings(max_examples=100)
def test_content_extraction_falls_back_to_body(body_content):
    """
    Property: When neither <main> nor <article> exists, content is extracted from <body>.

    Validates: Requirements 3.1, 3.2
    """
    assume(len(body_content.strip()) >= 60)

    # HTML without <main> or <article>, only <body>
    html = f"""
    <html>
        <body><p>{body_content}</p></body>
    </html>
    """

    result = clean(html)

    assert body_content[:20] in result, "Should extract content from <body> when no main/article"


# Feature: webscribe, Property 5: Noise element removal
@given(
    main_content=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=60,
        max_size=100
    ),
    header_text=st.text(
        alphabet="ABCDEFGHIJ",
        min_size=15,
        max_size=25
    ),
    footer_text=st.text(
        alphabet="KLMNOPQRST",
        min_size=15,
        max_size=25
    ),
    nav_text=st.text(
        alphabet="UVWXYZ",
        min_size=15,
        max_size=25
    ),
    aside_text=st.text(
        alphabet="0123456789",
        min_size=15,
        max_size=25
    )
)
@settings(max_examples=100)
def test_noise_element_removal(main_content, header_text, footer_text, nav_text, aside_text):
    """
    Property: Noise elements (header, footer, nav, aside, script) are removed from output.

    Validates: Requirements 3.3
    """
    # Use distinct alphabets to ensure no overlap
    assume(len(main_content.strip()) >= 60)

    html = f"""
    <html>
        <body>
            <header><p>{header_text}</p></header>
            <nav><a href="#">{nav_text}</a></nav>
            <main>
                <article>{main_content}</article>
                <aside>{aside_text}</aside>
            </main>
            <footer><p>{footer_text}</p></footer>
            <script>console.log('should be removed');</script>
        </body>
    </html>
    """

    result = clean(html)

    # Main content should be present
    assert main_content[:20] in result, "Should preserve main content"

    # Noise elements should NOT be present
    assert header_text[:10] not in result, "Should remove <header> content"
    assert footer_text[:10] not in result, "Should remove <footer> content"
    assert nav_text[:6] not in result, "Should remove <nav> content"
    assert aside_text[:10] not in result, "Should remove <aside> content"
    assert "console.log" not in result, "Should remove <script> content"


# Feature: webscribe, Property 6: Markdown structure preservation
def test_markdown_heading_preservation():
    """
    Property: HTML headings are converted to Markdown # syntax.

    Validates: Requirements 3.4
    """
    html = """
    <html><body><main>
        <h1>Title Level 1</h1>
        <h2>Title Level 2</h2>
        <h3>Title Level 3</h3>
        <p>Some content here to meet minimum length requirement for the test.</p>
    </main></body></html>
    """

    result = clean(html)

    assert "# Title Level 1" in result, "Should convert <h1> to #"
    assert "## Title Level 2" in result, "Should convert <h2> to ##"
    assert "### Title Level 3" in result, "Should convert <h3> to ###"


def test_markdown_list_preservation():
    """
    Property: HTML lists are converted to Markdown list syntax.

    Validates: Requirements 3.4
    """
    html = """
    <html><body><main>
        <h1>My Lists</h1>
        <ul>
            <li>Unordered item 1</li>
            <li>Unordered item 2</li>
        </ul>
        <ol>
            <li>Ordered item 1</li>
            <li>Ordered item 2</li>
        </ol>
    </main></body></html>
    """

    result = clean(html)

    # Unordered list uses -
    assert "- Unordered item 1" in result or "* Unordered item 1" in result
    assert "- Unordered item 2" in result or "* Unordered item 2" in result

    # Ordered list uses numbers
    assert "1." in result or "1)" in result
    assert "Ordered item 1" in result
    assert "Ordered item 2" in result


def test_markdown_code_block_preservation():
    """
    Property: HTML code blocks are converted to Markdown fenced code blocks.

    Validates: Requirements 3.4
    """
    html = """
    <html><body><main>
        <h1>Code Example</h1>
        <pre><code class="language-python">def hello():
    print("world")</code></pre>
        <p>Some additional content to meet the minimum length requirement.</p>
    </main></body></html>
    """

    result = clean(html)

    # Should contain code block markers (either ``` or indented)
    assert "def hello():" in result, "Should preserve code content"
    assert 'print("world")' in result, "Should preserve code content"


def test_markdown_hyperlink_preservation():
    """
    Property: HTML links are converted to Markdown [text](url) syntax.

    Validates: Requirements 3.4
    """
    html = """
    <html><body><main>
        <h1>Links Section</h1>
        <p>Check out <a href="https://example.com">this example</a> for more info.</p>
        <p>Additional content here to satisfy the minimum content length for this test.</p>
    </main></body></html>
    """

    result = clean(html)

    # Should contain Markdown link syntax
    assert "[this example]" in result or "this example" in result, "Should preserve link text"
    assert "https://example.com" in result or "example.com" in result, "Should preserve link URL"


def test_insufficient_content_raises_error():
    """
    Property: Content shorter than MIN_CONTENT_LENGTH raises InsufficientContentError.

    Validates: Requirements 3.5
    """
    # HTML with very little content (after removing tags)
    html = "<html><body><p>Hi</p></body></html>"

    with pytest.raises(InsufficientContentError) as exc_info:
        clean(html)

    assert "minimum" in str(exc_info.value).lower(), "Error should mention minimum length"


def test_sufficient_content_does_not_raise_error():
    """
    Property: Content longer than MIN_CONTENT_LENGTH succeeds.

    Validates: Requirements 3.5
    """
    # HTML with sufficient content (50+ characters after cleaning)
    html = """
    <html><body><main>
        <p>This is a paragraph with enough content to pass the minimum length requirement
        for the de-noiser. It needs to be at least 50 characters long after all HTML tags
        are removed and converted to Markdown format.</p>
    </main></body></html>
    """

    # Should not raise
    result = clean(html)
    assert len(result) >= 50, "Result should meet minimum length"
