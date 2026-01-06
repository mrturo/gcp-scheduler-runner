"""
Tests for missing coverage lines in src/auth.py and src/config.py.
"""

from src.config import TemplateResolver


def test_template_resolver_non_str():
    """Covers TemplateResolver.resolve early return for non-str (config.py:189)."""
    assert TemplateResolver.resolve(123) == 123
    assert TemplateResolver.resolve(["foo"]) == ["foo"]
