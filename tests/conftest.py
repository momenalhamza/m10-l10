"""Shared fixtures for the Lab 10 autograder.

Per the Autograder Test Path Rule, `..` (not `../starter/`) is the
correct insertion: in a learner's accepted repo, `api/` lives at the
repo root and `tests/` is a sibling. The `starter/` directory exists
only in this staging layout.
"""
import os
import sys
import warnings

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Silence third-party deprecation / resource warnings (typer, spaCy,
# passlib, httpx/starlette, huggingface) so the autograder output stays
# clean — they originate in dependencies, not learner code. Set both at
# import time and per-test (autouse), because some libraries reset the
# warning filters when they are imported, which would otherwise undo a
# one-time module-level call.
warnings.simplefilter("ignore")


@pytest.fixture(autouse=True)
def _silence_third_party_warnings():
    """Re-assert the ignore filter for each test (runs before other
    fixtures such as the TestClient, so fixture-setup warnings are
    suppressed too)."""
    warnings.simplefilter("ignore")
    yield
