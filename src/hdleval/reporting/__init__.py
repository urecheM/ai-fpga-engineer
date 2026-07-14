"""Automatic generation of publication-ready reports and figures."""

from __future__ import annotations

from .figures import write_all_figures
from .reports import write_all_reports

__all__ = ["write_all_figures", "write_all_reports"]
