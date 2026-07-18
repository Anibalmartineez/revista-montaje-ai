"""Domain primitives for Editor Offset Visual V2."""

from .layout_v2 import LAYOUT_SCHEMA_VERSION
from .validation import LayoutV2ValidationError, assert_valid_layout_v2, validate_layout_v2

__all__ = [
    "LAYOUT_SCHEMA_VERSION",
    "LayoutV2ValidationError",
    "assert_valid_layout_v2",
    "validate_layout_v2",
]
