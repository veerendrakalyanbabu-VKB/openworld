"""Regression tests for public documentation links."""

from scripts.validate_doc_links import validate


def test_documentation_links_are_valid():
    errors = validate()
    assert not errors, "Broken or disallowed links:\n" + "\n".join(errors)
