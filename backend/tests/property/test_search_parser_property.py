"""Property-based tests for search parser using Hypothesis."""

import pytest
from hypothesis import given, strategies as st, settings
from app.services.search_parser import (
    parse_search_query,
    extract_search_terms,
    has_field_restriction,
    SearchLexer,
    SearchParser,
)


class TestSearchParserProperties:
    """Property-based tests for search parser."""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_parse_never_crashes(self, query):
        """Test that any input doesn't crash the parser."""
        # Act
        result = parse_search_query(query)

        # Assert - should not raise exception
        assert result is not None
        assert isinstance(result.is_boolean, bool)
        assert result.original_query == query

    @given(
        st.lists(
            st.text(min_size=1, max_size=20).filter(lambda value: bool(value.strip())),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=50)
    def test_simple_terms_concatenation(self, terms):
        """Test that simple terms are parsed correctly."""
        # Arrange
        query = " ".join(terms)

        # Act
        result = parse_search_query(query)

        # Assert
        if not result.is_boolean:
            assert len(result.simple_terms) >= 1

    @given(
        st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    def test_single_word_parsing(self, word):
        """Test that single words are parsed correctly."""
        # Act
        result = parse_search_query(word)

        # Assert
        assert result is not None
        if not result.is_boolean:
            assert word in result.simple_terms

    @given(
        st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=3, max_size=15),
        st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=3, max_size=15),
    )
    @settings(max_examples=50)
    def test_and_operator_parsing(self, term1, term2):
        """Test that AND operator is recognized."""
        # Arrange
        query = f"{term1} AND {term2}"

        # Act
        result = parse_search_query(query)

        # Assert
        assert result.is_boolean is True
        assert result.expression is not None

    @given(
        st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=3, max_size=15),
        st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=3, max_size=15),
    )
    @settings(max_examples=50)
    def test_or_operator_parsing(self, term1, term2):
        """Test that OR operator is recognized."""
        # Arrange
        query = f"{term1} OR {term2}"

        # Act
        result = parse_search_query(query)

        # Assert
        assert result.is_boolean is True
        assert result.expression is not None

    @given(st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=3, max_size=15))
    @settings(max_examples=30)
    def test_not_operator_parsing(self, term):
        """Test that NOT operator is recognized."""
        # Arrange
        query = f"NOT {term}"

        # Act
        result = parse_search_query(query)

        # Assert
        assert result.is_boolean is True

    @given(
        st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=3, max_size=20)
    )
    @settings(max_examples=30)
    def test_quoted_phrase_parsing(self, phrase):
        """Test that quoted phrases are parsed correctly."""
        # Arrange
        query = f'"{phrase}"'

        # Act
        result = parse_search_query(query)

        # Assert
        assert result.is_boolean is True

    @given(
        st.sampled_from(["title", "company", "location", "description"]),
        st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=3, max_size=20),
    )
    @settings(max_examples=50)
    def test_field_restriction_parsing(self, field, value):
        """Test that field restrictions are parsed correctly."""
        # Arrange
        query = f"{field}:{value}"

        # Act
        result = parse_search_query(query)
        has_field = has_field_restriction(result, field)

        # Assert
        assert result.is_boolean is True
        assert has_field is True

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_extract_terms_never_crashes(self, query):
        """Test that extract_search_terms never crashes."""
        # Arrange
        parsed = parse_search_query(query)

        # Act
        terms = extract_search_terms(parsed)

        # Assert
        assert isinstance(terms, list)
        assert all(isinstance(term, str) for term in terms)

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=50)
    def test_lexer_never_crashes(self, query):
        """Test that lexer never crashes."""
        # Act
        lexer = SearchLexer(query)

        # Assert
        assert len(lexer.tokens) >= 1  # At least EOF token
        assert lexer.tokens[-1].value == ""  # Last token is EOF

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=50)
    def test_parser_never_crashes(self, query):
        """Test that parser never crashes on valid tokens."""
        # Arrange
        lexer = SearchLexer(query)

        # Act
        parser = SearchParser(lexer.tokens)

        # Assert - parser should be created without error
        assert parser is not None

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3))
    @settings(max_examples=30)
    def test_empty_and_short_queries(self, terms):
        """Test handling of empty and very short queries."""
        # Arrange
        query = " ".join(terms)

        # Act
        result = parse_search_query(query)

        # Assert
        assert result is not None
        if not query.strip():
            assert result.is_boolean is False


class TestSearchQueryEdgeCases:
    """Edge case tests for search parser."""

    @pytest.mark.parametrize(
        "query",
        [
            "",  # Empty
            "   ",  # Whitespace only
            "!!!",  # Special characters only
            "12345",  # Numbers only
            "_underscore_",  # Underscore
            "with-dash",  # Dashes
            "dot.separated",  # Dots
            "UPPERCASE",  # All uppercase
            "lowercase",  # All lowercase
            "MixedCase",  # Mixed case
            "with123numbers456",  # Numbers mixed
        ],
    )
    def test_various_edge_cases(self, query):
        """Test that various edge cases don't crash."""
        result = parse_search_query(query)
        assert result is not None

    @pytest.mark.parametrize(
        "query,expected_field",
        [
            ("title:python", "title"),
            ("company:google", "company"),
            ("location:remote", "location"),
            ("description:something", "description"),
        ],
    )
    def test_field_restrictions(self, query, expected_field):
        """Test field restrictions are detected."""
        result = parse_search_query(query)
        assert has_field_restriction(result, expected_field)

    @pytest.mark.parametrize(
        "query",
        [
            "(python)",
            "((python))",
            "(python AND java)",
            "((python OR java) AND remote)",
        ],
    )
    def test_nested_parentheses(self, query):
        """Test nested parentheses parsing."""
        result = parse_search_query(query)
        assert result.is_boolean is True
        assert result.expression is not None
