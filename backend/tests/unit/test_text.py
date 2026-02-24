"""Unit tests for text utilities."""

import pytest

from app.utils.text import clean_text_for_embedding


class TestCleanTextForEmbedding:
    """Test suite for clean_text_for_embedding function."""

    def test_empty_text(self):
        """Test cleaning empty text."""
        # Act
        result = clean_text_for_embedding("")

        # Assert
        assert result == ""

    def test_none_text(self):
        """Test cleaning None text."""
        # Act
        result = clean_text_for_embedding(None)

        # Assert
        assert result == ""

    def test_removes_html_tags(self):
        """Test that HTML tags are removed."""
        # Arrange
        text = "<p>This is a <strong>test</strong> with <em>HTML</em>.</p>"

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "<p>" not in result
        assert "<strong>" not in result
        assert result == "This is a test with HTML ."

    def test_removes_html_entities(self):
        """Test that HTML entities are removed."""
        # Arrange
        text = "Test &amp; example with &lt;tags&gt; and &nbsp;space"

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "&amp;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result
        assert "&nbsp;" not in result

    def test_normalizes_whitespace(self):
        """Test that whitespace is normalized."""
        # Arrange
        text = "This    has    too    much   whitespace\n\nand\t\ttabs"

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "  " not in result  # No double spaces
        assert result == "This has too much whitespace and tabs"

    def test_trims_whitespace(self):
        """Test that leading/trailing whitespace is trimmed."""
        # Arrange
        text = "   surrounded by spaces   "

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert result == "surrounded by spaces"

    def test_ascii_text_limit(self):
        """Test ASCII text length limit."""
        # Arrange
        text = "x" * 10000

        # Act
        result = clean_text_for_embedding(text, max_chars_ascii=1000, max_chars_unicode=500)

        # Assert
        assert len(result) == 1000

    def test_unicode_text_limit(self):
        """Test Unicode text length limit."""
        # Arrange
        text = "日本語" * 1000

        # Act
        result = clean_text_for_embedding(text, max_chars_ascii=6000, max_chars_unicode=100)

        # Assert
        assert len(result) == 100

    def test_mixed_text_uses_ascii_limit(self):
        """Test that mostly ASCII text uses ASCII limit."""
        # Arrange
        text = "English text with a few unicode chars: café résumé"

        # Act
        result = clean_text_for_embedding(text, max_chars_ascii=50, max_chars_unicode=10)

        # Assert
        # Should use ASCII limit since >80% of chars are ASCII
        assert len(result) <= 50

    def test_complex_html_document(self):
        """Test cleaning a complex HTML document."""
        # Arrange
        text = """
        <html>
            <body>
                <h1>Job Title</h1>
                <p>Description with <strong>bold</strong> text.
                And <a href="link">a link</a>.</p>
            </body>
        </html>
        """

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "<" not in result
        assert ">" not in result
        assert "Job Title" in result
        assert "Description with bold text" in result
        assert "a link" in result

    def test_preserves_important_content(self):
        """Test that important content is preserved."""
        # Arrange
        text = "Software Engineer at Google - Python, JavaScript, AWS"

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "Software Engineer" in result
        assert "Google" in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "AWS" in result

    def test_handles_special_characters(self):
        """Test handling of special characters."""
        # Arrange
        text = "C++ developer with C# experience. Knowledge of SQL/NoSQL."

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "C++" in result
        assert "C#" in result
        assert "SQL/NoSQL" in result

    def test_handles_code_snippets(self):
        """Test handling of code snippets in text."""
        # Arrange
        text = """
        Requirements:
        ```python
        def hello():
            print("Hello World")
        ```
        Experience with code reviews.
        """

        # Act
        result = clean_text_for_embedding(text)

        # Assert
        assert "```" not in result
        assert "def hello()" in result
        assert "Hello World" in result
        assert "code reviews" in result
