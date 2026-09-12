"""Canonical acceptance thresholds shared by V2 output evidence.

These values describe the comparison contract; they do not enable an output
gate or change Layout V2 persistence.
"""

from __future__ import annotations

from typing import Final


OUTPUT_PARITY_SCHEMA_VERSION: Final = 1
PDF_BOX_TOLERANCE_MM: Final = 0.01
CANVAS_GEOMETRY_TOLERANCE_MM: Final = 0.01
PAGE_ORDER_EXACT: Final = True
ROTATION_AND_FLIP_EXACT: Final = True
PREVIEW_PDF_MAX_CHANGED_RATIO: Final = 0.02
PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA: Final = 8.0
DERIVED_PREVIEW_MAX_CHANGED_RATIO: Final = 0.08
DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA: Final = 12.0


__all__ = [
    "CANVAS_GEOMETRY_TOLERANCE_MM",
    "DERIVED_PREVIEW_MAX_CHANGED_RATIO",
    "DERIVED_PREVIEW_MAX_MEAN_CHANNEL_DELTA",
    "OUTPUT_PARITY_SCHEMA_VERSION",
    "PAGE_ORDER_EXACT",
    "PDF_BOX_TOLERANCE_MM",
    "PREVIEW_PDF_MAX_CHANGED_RATIO",
    "PREVIEW_PDF_MAX_MEAN_CHANNEL_DELTA",
    "ROTATION_AND_FLIP_EXACT",
]
