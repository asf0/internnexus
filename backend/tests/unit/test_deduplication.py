"""Unit tests for pipeline/utils/deduplication.py."""

import pytest

from pipeline.utils.deduplication import deduplicate_by_key


class TestDeduplicateByKey:
    """Test suite for deduplicate_by_key function."""

    def test_deduplicate_with_duplicate_items(self):
        items = [
            {"id": "a", "value": 1},
            {"id": "b", "value": 2},
            {"id": "a", "value": 3},
            {"id": "c", "value": 4},
            {"id": "b", "value": 5},
        ]

        result = deduplicate_by_key(items, lambda x: x["id"])

        assert len(result) == 3
        assert result[0] == {"id": "a", "value": 1}
        assert result[1] == {"id": "b", "value": 2}
        assert result[2] == {"id": "c", "value": 4}

    def test_deduplicate_with_unique_items(self):
        items = [
            {"id": "a", "value": 1},
            {"id": "b", "value": 2},
            {"id": "c", "value": 3},
        ]

        result = deduplicate_by_key(items, lambda x: x["id"])

        assert len(result) == 3
        assert result == items

    def test_deduplicate_with_empty_list(self):
        result = deduplicate_by_key([], lambda x: x["id"])
        assert result == []

    def test_deduplicate_preserves_first_occurrence(self):
        items = [
            {"id": "dup", "value": "first"},
            {"id": "dup", "value": "second"},
            {"id": "dup", "value": "third"},
        ]

        result = deduplicate_by_key(items, lambda x: x["id"])

        assert len(result) == 1
        assert result[0]["value"] == "first"

    def test_deduplicate_with_string_items(self):
        items = ["apple", "banana", "apple", "cherry", "banana"]

        result = deduplicate_by_key(items, lambda x: x)

        assert result == ["apple", "banana", "cherry"]

    def test_deduplicate_with_integer_items(self):
        items = [1, 2, 3, 2, 1, 4, 5, 4]

        result = deduplicate_by_key(items, lambda x: str(x))

        assert result == [1, 2, 3, 4, 5]

    def test_deduplicate_key_function_called_correctly(self):
        call_count = 0
        items = [{"id": "a"}, {"id": "b"}, {"id": "a"}]

        def counting_key_func(item):
            nonlocal call_count
            call_count += 1
            return item["id"]

        deduplicate_by_key(items, counting_key_func)

        assert call_count == 3

    def test_deduplicate_with_complex_key(self):
        items = [
            {"first": "John", "last": "Doe"},
            {"first": "Jane", "last": "Smith"},
            {"first": "John", "last": "Doe"},
            {"first": "John", "last": "Smith"},
        ]

        result = deduplicate_by_key(items, lambda x: f"{x['first']}_{x['last']}")

        assert len(result) == 3
        assert result[0] == {"first": "John", "last": "Doe"}
        assert result[1] == {"first": "Jane", "last": "Smith"}
        assert result[2] == {"first": "John", "last": "Smith"}

    def test_deduplicate_with_none_key(self):
        items = [
            {"id": None, "value": 1},
            {"id": None, "value": 2},
            {"id": "a", "value": 3},
        ]

        result = deduplicate_by_key(items, lambda x: str(x["id"]))

        assert len(result) == 2
        assert result[0]["value"] == 1
        assert result[1]["value"] == 3

    def test_deduplicate_with_case_sensitive_keys(self):
        items = [
            {"id": "ABC"},
            {"id": "abc"},
            {"id": "ABC"},
        ]

        result = deduplicate_by_key(items, lambda x: x["id"])

        assert len(result) == 2
        assert result[0]["id"] == "ABC"
        assert result[1]["id"] == "abc"

    def test_deduplicate_with_whitespace_keys(self):
        items = [
            {"id": "key"},
            {"id": "key "},
            {"id": " key"},
            {"id": "key"},
        ]

        result = deduplicate_by_key(items, lambda x: x["id"])

        assert len(result) == 3

    def test_deduplicate_large_list(self):
        items = [{"id": i % 100} for i in range(1000)]

        result = deduplicate_by_key(items, lambda x: str(x["id"]))

        assert len(result) == 100

    def test_deduplicate_with_tuple_items(self):
        items = [
            ("a", 1),
            ("b", 2),
            ("a", 3),
            ("c", 4),
        ]

        result = deduplicate_by_key(items, lambda x: x[0])

        assert len(result) == 3
        assert result[0] == ("a", 1)
        assert result[1] == ("b", 2)
        assert result[2] == ("c", 4)

    def test_deduplicate_with_custom_object(self):
        class Item:
            def __init__(self, key, value):
                self.key = key
                self.value = value

        items = [
            Item("a", 1),
            Item("b", 2),
            Item("a", 3),
        ]

        result = deduplicate_by_key(items, lambda x: x.key)

        assert len(result) == 2
        assert result[0].value == 1
        assert result[1].value == 2
