"""Automatic generation of publication-ready reports and figures."""
from __future__ import annotations

from .reports import write_all_reports
from .figures import write_all_figures

__all__ = ["write_all_reports", "write_all_figures"]
