"""Unit tests for search parser module."""

from app.services.search_parser import (
    TokenType,
    SearchTerm,
    BooleanExpr,
    ParsedSearch,
    SearchLexer,
    SearchParser,
    parse_search_query,
    extract_search_terms,
    has_field_restriction,
)


class TestSearchLexer:
    """Test suite for SearchLexer."""

    def test_tokenize_simple_word(self):
        """Test tokenizing a simple word."""
        # Act
        lexer = SearchLexer("python")

        # Assert
        assert len(lexer.tokens) == 2  # WORD + EOF
        assert lexer.tokens[0].type == TokenType.WORD
        assert lexer.tokens[0].value == "python"

    def test_tokenize_and_operator(self):
        """Test tokenizing AND operator."""
        # Act
        lexer = SearchLexer("python AND developer")

        # Assert
        assert lexer.tokens[0].type == TokenType.WORD
        assert lexer.tokens[0].value == "python"
        assert lexer.tokens[1].type == TokenType.AND
        assert lexer.tokens[2].type == TokenType.WORD
        assert lexer.tokens[2].value == "developer"

    def test_tokenize_or_operator(self):
        """Test tokenizing OR operator."""
        # Act
        lexer = SearchLexer("python OR java")

        # Assert
        assert lexer.tokens[1].type == TokenType.OR

    def test_tokenize_not_operator(self):
        """Test tokenizing NOT operator."""
        # Act
        lexer = SearchLexer("NOT junior")

        # Assert
        assert lexer.tokens[0].type == TokenType.NOT
        assert lexer.tokens[1].type == TokenType.WORD
        assert lexer.tokens[1].value == "junior"

    def test_tokenize_quoted_phrase(self):
        """Test tokenizing quoted phrase."""
        # Act
        lexer = SearchLexer('"software engineer"')

        # Assert
        assert lexer.tokens[0].type == TokenType.QUOTE
        assert lexer.tokens[0].value == "software engineer"

    def test_tokenize_field(self):
        """Test tokenizing field-specific search."""
        # Act
        lexer = SearchLexer("title:python")

        # Assert
        assert lexer.tokens[0].type == TokenType.FIELD
        assert lexer.tokens[0].field == "title"
        assert lexer.tokens[0].value == "python"

    def test_tokenize_parentheses(self):
        """Test tokenizing parentheses."""
        # Act
        lexer = SearchLexer("(python OR java)")

        # Assert
        assert lexer.tokens[0].type == TokenType.LPAREN
        assert lexer.tokens[3].type == TokenType.RPAREN

    def test_tokenize_case_insensitive_operators(self):
        """Test that operators are case insensitive."""
        # Act
        lexer = SearchLexer("python and java OR cpp not senior")

        # Assert
        assert lexer.tokens[1].type == TokenType.AND
        assert lexer.tokens[3].type == TokenType.OR
        assert lexer.tokens[5].type == TokenType.NOT

    def test_tokenize_complex_query(self):
        """Test tokenizing a complex query."""
        # Arrange
        query = '(python OR "machine learning") AND title:senior NOT junior'

        # Act
        lexer = SearchLexer(query)

        # Assert
        token_types = [t.type for t in lexer.tokens[:-1]]  # Exclude EOF
        assert token_types == [
            TokenType.LPAREN,
            TokenType.WORD,
            TokenType.OR,
            TokenType.QUOTE,
            TokenType.RPAREN,
            TokenType.AND,
            TokenType.FIELD,
            TokenType.NOT,
            TokenType.WORD,
        ]


class TestSearchParser:
    """Test suite for SearchParser."""

    def test_parse_simple_term(self):
        """Test parsing a simple term."""
        # Arrange
        lexer = SearchLexer("python")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert isinstance(result, BooleanExpr)
        assert result.operator == "AND"
        assert len(result.terms) == 1
        assert isinstance(result.terms[0], SearchTerm)
        assert result.terms[0].value == "python"

    def test_parse_and_expression(self):
        """Test parsing AND expression."""
        # Arrange
        lexer = SearchLexer("python AND developer")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.operator == "AND"
        assert len(result.terms) == 2
        assert result.terms[0].value == "python"
        assert result.terms[1].value == "developer"

    def test_parse_or_expression(self):
        """Test parsing OR expression."""
        # Arrange
        lexer = SearchLexer("python OR java")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.operator == "OR"
        assert len(result.terms) == 2

    def test_parse_not_expression(self):
        """Test parsing NOT expression."""
        # Arrange
        lexer = SearchLexer("NOT junior")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.operator == "NOT"
        assert len(result.terms) == 1
        assert result.terms[0].value == "junior"

    def test_parse_parentheses(self):
        """Test parsing parenthesized expression."""
        # Arrange
        lexer = SearchLexer("(python OR java) AND developer")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.operator == "AND"
        assert len(result.terms) == 2
        # First term should be the OR expression
        assert isinstance(result.terms[0], BooleanExpr)
        assert result.terms[0].operator == "OR"

    def test_parse_quoted_phrase(self):
        """Test parsing quoted phrase."""
        # Arrange
        lexer = SearchLexer('"software engineer"')
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.terms[0].value == "software engineer"
        assert result.terms[0].is_exact is True

    def test_parse_field_restriction(self):
        """Test parsing field-specific search."""
        # Arrange
        lexer = SearchLexer("title:python")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.terms[0].value == "python"
        assert result.terms[0].field == "title"

    def test_parse_invalid_field(self):
        """Test that invalid fields are treated as None."""
        # Arrange
        lexer = SearchLexer("invalid:python")
        parser = SearchParser(lexer.tokens)

        # Act
        result = parser.parse()

        # Assert
        assert result.terms[0].field is None


class TestParseSearchQuery:
    """Test suite for parse_search_query function."""

    def test_empty_query(self):
        """Test parsing empty query."""
        # Act
        result = parse_search_query("")

        # Assert
        assert result.is_boolean is False
        assert result.original_query == ""
        assert result.expression is None

    def test_whitespace_only_query(self):
        """Test parsing whitespace-only query."""
        # Act
        result = parse_search_query("   ")

        # Assert
        assert result.is_boolean is False

    def test_simple_terms_query(self):
        """Test parsing simple terms without boolean operators."""
        # Act
        result = parse_search_query("python developer remote")

        # Assert
        assert result.is_boolean is False
        assert result.simple_terms == ["python", "developer", "remote"]

    def test_boolean_query(self):
        """Test parsing query with boolean operators."""
        # Act
        result = parse_search_query("python AND developer")

        # Assert
        assert result.is_boolean is True
        assert result.expression is not None

    def test_query_with_quotes(self):
        """Test parsing query with quotes triggers boolean mode."""
        # Act
        result = parse_search_query('"software engineer"')

        # Assert
        assert result.is_boolean is True

    def test_query_with_fields(self):
        """Test parsing query with field specifiers triggers boolean mode."""
        # Act
        result = parse_search_query("title:python")

        # Assert
        assert result.is_boolean is True

    def test_invalid_query_fallback(self):
        """Test that invalid queries fall back to simple terms."""
        # Act
        result = parse_search_query("AND OR NOT")  # Invalid boolean expression

        # Assert
        assert result.is_boolean is False
        assert len(result.simple_terms) > 0


class TestExtractSearchTerms:
    """Test suite for extract_search_terms function."""

    def test_extract_from_simple_terms(self):
        """Test extracting from simple terms query."""
        # Arrange
        parsed = ParsedSearch(
            is_boolean=False,
            original_query="python developer",
            simple_terms=["python", "developer"],
        )

        # Act
        terms = extract_search_terms(parsed)

        # Assert
        assert terms == ["python", "developer"]

    def test_extract_from_boolean_expr(self):
        """Test extracting from boolean expression."""
        # Arrange
        parsed = parse_search_query("python OR java NOT cpp")

        # Act
        terms = extract_search_terms(parsed)

        # Assert
        assert "python" in terms
        assert "java" in terms
        assert "cpp" in terms

    def test_extract_excludes_exact_phrases(self):
        """Test that exact phrases are excluded."""
        # Arrange
        parsed = parse_search_query('python "exact phrase" developer')

        # Act
        terms = extract_search_terms(parsed)

        # Assert
        assert "python" in terms
        assert "developer" in terms
        assert "exact phrase" not in terms  # Exact phrases excluded


class TestHasFieldRestriction:
    """Test suite for has_field_restriction function."""

    def test_has_field_restriction_true(self):
        """Test detecting field restriction."""
        # Arrange
        parsed = parse_search_query("title:python")

        # Act
        result = has_field_restriction(parsed, "title")

        # Assert
        assert result is True

    def test_has_field_restriction_false(self):
        """Test when no field restriction."""
        # Arrange
        parsed = parse_search_query("python developer")

        # Act
        result = has_field_restriction(parsed, "title")

        # Assert
        assert result is False

    def test_has_field_restriction_different_field(self):
        """Test with different field restriction."""
        # Arrange
        parsed = parse_search_query("company:google")

        # Act
        result = has_field_restriction(parsed, "title")

        # Assert
        assert result is False

    def test_has_field_in_nested_expr(self):
        """Test detecting field in nested expression."""
        # Arrange
        parsed = parse_search_query("(title:python OR company:google)")

        # Act
        result = has_field_restriction(parsed, "title")

        # Assert
        assert result is True
