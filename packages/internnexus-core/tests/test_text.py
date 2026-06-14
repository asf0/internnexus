"""Unit tests for core text utilities."""

from internnexus_core.text import clean_text_for_embedding


class TestCleanTextForEmbedding:
    """Test suite for clean_text_for_embedding function."""

    def test_empty_text(self):
        result = clean_text_for_embedding("")
        assert result == ""

    def test_none_text(self):
        result = clean_text_for_embedding(None)
        assert result == ""

    def test_removes_html_tags(self):
        text = "<p>This is a <strong>test</strong> with <em>HTML</em>.</p>"
        result = clean_text_for_embedding(text)
        assert "<p>" not in result
        assert "<strong>" not in result
        assert result == "This is a test with HTML ."

    def test_removes_html_entities(self):
        text = "Test &amp; example with &lt;tags&gt; and &nbsp;space"
        result = clean_text_for_embedding(text)
        assert "&amp;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result
        assert "&nbsp;" not in result

    def test_normalizes_whitespace(self):
        text = "This    has    too    much   whitespace\n\nand\t\ttabs"
        result = clean_text_for_embedding(text)
        assert "  " not in result
        assert result == "This has too much whitespace and tabs"

    def test_ascii_text_limit(self):
        text = "x" * 10000
        result = clean_text_for_embedding(text, max_chars_ascii=1000, max_chars_unicode=500)
        assert len(result) == 1000

    def test_unicode_text_limit(self):
        text = "日本語" * 1000
        result = clean_text_for_embedding(text, max_chars_ascii=6000, max_chars_unicode=100)
        assert len(result) == 100

    def test_mixed_text_uses_ascii_limit(self):
        text = "English text with a few unicode chars: café résumé"
        result = clean_text_for_embedding(text, max_chars_ascii=50, max_chars_unicode=10)
        assert len(result) <= 50

    def test_removes_markdown_code_fences(self):
        text = "```python\ndef hello():\n    print('hi')\n```"
        result = clean_text_for_embedding(text)
        assert "```" not in result
        assert "def hello()" in result
