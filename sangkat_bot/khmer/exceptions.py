# Vendored from KAI_AI shared/kai_khmer (same author), 2026-11-21. Do not edit here; re-copy instead.
"""
Module: exceptions.py
Purpose: Define explicit tokenizer configuration and setup exceptions.
Usage: from sangkat_bot.khmer.exceptions import InvalidConfigurationError
"""

from __future__ import annotations


class TokenizerError(Exception):
    """Base exception for tokenizer configuration and processing failures."""


class InvalidConfigurationError(TokenizerError):
    """Raised when a tokenizer configuration is missing or invalid."""


class MalformedModelError(TokenizerError):
    """Raised when a model or lexicon artifact cannot be loaded."""


class TokenizerSetupError(TokenizerError):
    """Raised when tokenizer initialization cannot be completed."""


__all__ = [
    "InvalidConfigurationError",
    "MalformedModelError",
    "TokenizerError",
    "TokenizerSetupError",
]
