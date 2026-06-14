"""Boolean search query parser for job searches.

Supports:
- AND: "python AND remote"
- OR: "python OR java"
- NOT: "python NOT senior"
- Quoted phrases: '"software engineer"'
- Field-specific: "title:python company:google"
- Parentheses for grouping: "(python OR java) AND remote"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto


class TokenType(Enum):
    WORD = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    QUOTE = auto()
    FIELD = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    field: str | None = None


@dataclass
class SearchTerm:
    value: str
    field: str | None = None
    is_exact: bool = False


@dataclass
class BooleanExpr:
    operator: str  # "AND", "OR", "NOT"
    terms: list[SearchTerm | BooleanExpr] = field(default_factory=list)


@dataclass
class ParsedSearch:
    is_boolean: bool
    original_query: str
    expression: BooleanExpr | None = None
    simple_terms: list[str] = field(default_factory=list)


class SearchLexer:
    TOKEN_PATTERNS = [
        (r'"([^"]*)"', TokenType.QUOTE),
        (r"(\bAND\b)", TokenType.AND),
        (r"(\bOR\b)", TokenType.OR),
        (r"(\bNOT\b)", TokenType.NOT),
        (r"(\()", TokenType.LPAREN),
        (r"(\))", TokenType.RPAREN),
        (r'(\w+):(\w+|\([^)]+\)|"[^"]*")', TokenType.FIELD),
        (r"([^\s()]+)", TokenType.WORD),
    ]

    def __init__(self, query: str):
        self.query = query
        self.pos = 0
        self.tokens: list[Token] = []
        self._tokenize()

    def _tokenize(self) -> None:
        while self.pos < len(self.query):
            if self.query[self.pos].isspace():
                self.pos += 1
                continue

            matched = False
            for pattern, token_type in self.TOKEN_PATTERNS:
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(self.query, self.pos)
                if match:
                    if token_type == TokenType.FIELD:
                        field_name = match.group(1)
                        field_value = match.group(2)
                        self.tokens.append(Token(token_type, field_value, field=field_name))
                    elif token_type == TokenType.QUOTE:
                        self.tokens.append(Token(token_type, match.group(1)))
                    else:
                        self.tokens.append(Token(token_type, match.group(1)))
                    self.pos = match.end()
                    matched = True
                    break

            if not matched:
                self.pos += 1

        self.tokens.append(Token(TokenType.EOF, ""))


class SearchParser:
    VALID_FIELDS = {"title", "company", "location", "description"}

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: TokenType | None = None) -> Token:
        token = self.current()
        if expected_type and token.type != expected_type:
            raise ValueError(f"Expected {expected_type}, got {token.type}")
        self.pos += 1
        return token

    def parse(self) -> BooleanExpr:
        return self.parse_or()

    def parse_or(self) -> BooleanExpr:
        left = self.parse_and()

        terms: list[BooleanExpr | SearchTerm] = [left]
        while self.current().type == TokenType.OR:
            self.consume(TokenType.OR)
            terms.append(self.parse_and())

        if len(terms) == 1:
            return terms[0] if isinstance(terms[0], BooleanExpr) else BooleanExpr("AND", terms)

        return BooleanExpr("OR", terms)

    def parse_and(self) -> BooleanExpr:
        left = self.parse_not()

        terms: list[BooleanExpr | SearchTerm] = [left]
        while self.current().type not in (TokenType.OR, TokenType.EOF, TokenType.RPAREN):
            if self.current().type == TokenType.AND:
                self.consume(TokenType.AND)
            terms.append(self.parse_not())

        if len(terms) == 1:
            return terms[0] if isinstance(terms[0], BooleanExpr) else BooleanExpr("AND", terms)

        return BooleanExpr("AND", terms)

    def parse_not(self) -> BooleanExpr | SearchTerm:
        if self.current().type == TokenType.NOT:
            self.consume(TokenType.NOT)
            term = self.parse_primary()
            return BooleanExpr("NOT", [term])
        return self.parse_primary()

    def parse_primary(self) -> BooleanExpr | SearchTerm:
        token = self.current()

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_or()
            self.consume(TokenType.RPAREN)
            return expr

        if token.type == TokenType.FIELD:
            self.consume()
            field_name = token.field.lower() if token.field else ""
            if field_name not in self.VALID_FIELDS:
                field_name = None
            return SearchTerm(token.value, field=field_name)

        if token.type == TokenType.QUOTE:
            self.consume()
            return SearchTerm(token.value, is_exact=True)

        if token.type == TokenType.WORD:
            self.consume()
            return SearchTerm(token.value)

        raise ValueError(f"Unexpected token: {token.type}")


def parse_search_query(query: str) -> ParsedSearch:
    """Parse a search query and determine if it uses boolean operators.

    Args:
        query: Raw search query string

    Returns:
        ParsedSearch with boolean expression or simple terms
    """
    if not query or not query.strip():
        return ParsedSearch(is_boolean=False, original_query=query)

    original_query = query
    query = query.strip()

    has_boolean = bool(
        re.search(r"\bAND\b", query, re.IGNORECASE)
        or re.search(r"\bOR\b", query, re.IGNORECASE)
        or re.search(r"\bNOT\b", query, re.IGNORECASE)
        or ":" in query
        or '"' in query
        or "(" in query
        or ")" in query
    )

    if not has_boolean:
        simple_terms = query.split()
        return ParsedSearch(
            is_boolean=False, original_query=original_query, simple_terms=simple_terms
        )

    try:
        lexer = SearchLexer(query)
        parser = SearchParser(lexer.tokens)
        expr = parser.parse()
        return ParsedSearch(is_boolean=True, original_query=original_query, expression=expr)
    except Exception as e:  # noqa: BLE001  # intentional fallback: any parse failure degrades to simple terms
        import logging

        logging.getLogger(__name__).warning(f"Failed to parse boolean query '{query}': {e}")
        simple_terms = re.findall(r"\b\w+\b", query)
        return ParsedSearch(
            is_boolean=False, original_query=original_query, simple_terms=simple_terms
        )


def extract_search_terms(parsed: ParsedSearch) -> list[str]:
    """Extract all search terms from a parsed query for embedding."""
    terms: list[str] = []

    def extract_from_expr(expr: BooleanExpr | SearchTerm) -> None:
        if isinstance(expr, SearchTerm):
            if not expr.is_exact:
                terms.append(expr.value)
        elif isinstance(expr, BooleanExpr):
            for term in expr.terms:
                extract_from_expr(term)

    if parsed.is_boolean and parsed.expression:
        extract_from_expr(parsed.expression)
    else:
        terms.extend(parsed.simple_terms)

    return terms


def has_field_restriction(parsed: ParsedSearch, field: str) -> bool:
    """Check if query has restrictions on a specific field."""

    def check_expr(expr: BooleanExpr | SearchTerm) -> bool:
        if isinstance(expr, SearchTerm):
            return expr.field == field.lower()
        elif isinstance(expr, BooleanExpr):
            return any(check_expr(t) for t in expr.terms)
        return False

    if parsed.is_boolean and parsed.expression:
        return check_expr(parsed.expression)
    return False
