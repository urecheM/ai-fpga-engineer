"""Centralised structured (JSONL) logging for every experiment stage."""

from __future__ import annotations

from .structured import StageEvent, StructuredLogger

__all__ = ["StageEvent", "StructuredLogger"]
