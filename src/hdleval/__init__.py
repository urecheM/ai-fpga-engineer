"""hdleval — LLM-Assisted Hardware Design Research Platform.

A reproducible experimental framework for evaluating AI-assisted hardware
design methodologies. The package is deliberately layered so that model
inference, benchmark definition, and evaluation are independent and
config-driven; see ``docs/research-specification.md`` for the full design.
"""

from __future__ import annotations

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0"

__all__ = ["SCHEMA_VERSION", "__version__"]
