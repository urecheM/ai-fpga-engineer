"""Verification: reference-vector simulation, property checks, failure classes."""
from __future__ import annotations

from .properties import PropertyReport, check_properties
from .failures import FailureClass, classify_failure

__all__ = ["PropertyReport", "check_properties", "FailureClass", "classify_failure"]
