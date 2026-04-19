from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolRequest:
    name: str
    args: Dict[str, Any]


@dataclass
class ToolResponse:
    success: bool
    layout: Optional[Dict[str, Any]] = None
    message: str = ""
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
