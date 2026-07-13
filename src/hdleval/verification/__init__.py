"""Verification: reference-vector simulation, property checks, failure classes."""

from __future__ import annotations

from .failures import FailureClass, classify_failure
from .properties import PropertyReport, check_properties

__all__ = ["FailureClass", "PropertyReport", "check_properties", "classify_failure"]
