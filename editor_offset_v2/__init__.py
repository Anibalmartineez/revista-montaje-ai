"""Editor Offset Visual V2.

This package is intentionally isolated from the legacy editor.  Phase 1 only
defines the persisted layout contract and its strict validator.
"""

from .domain.layout_v2 import LAYOUT_SCHEMA_VERSION

__all__ = ["LAYOUT_SCHEMA_VERSION"]
