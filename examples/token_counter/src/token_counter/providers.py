"""Tokenizer ports and deliberately simple offline adapters."""

import re
from typing import Protocol


class Tokenizer(Protocol):
    """The only capability required by the budget domain."""

    name: str

    def count(self, text: str) -> int:
        """Return the number of units used by *this* tokenizer."""


class WhitespaceTokenizer:
    """Deterministic word-like fake for policy tests, never billing."""

    name = "fixture-whitespace-v1"

    def count(self, text: str) -> int:
        return len(re.findall(r"\S+", text))


class Utf8ByteTokenizer:
    """UTF-8 byte counter used to demonstrate multilingual differences."""

    name = "fixture-utf8-bytes-v1"

    def count(self, text: str) -> int:
        return len(text.encode("utf-8"))
