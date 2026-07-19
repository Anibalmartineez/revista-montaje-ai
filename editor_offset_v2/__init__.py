"""Editor Offset Visual V2.

This package is intentionally isolated from the legacy editor.
"""

from .domain.layout_v2 import LAYOUT_SCHEMA_VERSION
from .infrastructure.editor_output_adapter import (
    adapt_layout_v2_to_output,
    serialize_output_job,
)

__all__ = [
    "LAYOUT_SCHEMA_VERSION",
    "adapt_layout_v2_to_output",
    "serialize_output_job",
]
