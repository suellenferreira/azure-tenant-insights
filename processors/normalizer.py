"""
Data normalization utilities shared across writers and processors.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_str(value: Any, max_length: int = 32767) -> str:
    """
    Safely converts any value to a string suitable for Excel cells.
    Excel cells have a hard limit of 32,767 characters.
    Dicts/lists are JSON-serialized. None becomes empty string.
    """
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            result = json.dumps(value, ensure_ascii=False)
        except Exception:
            result = str(value)
    else:
        result = str(value)

    if len(result) > max_length:
        result = result[: max_length - 3] + "..."

    return result


def clean_resource_type(resource_type: str) -> str:
    """
    Converts a full resource type string to a display-friendly name.
    Example: 'microsoft.compute/virtualmachines' -> 'VirtualMachines'
    """
    if "/" in resource_type:
        _, resource_name = resource_type.rsplit("/", 1)
        return resource_name.replace("-", "").title().replace(" ", "")
    return resource_type.title()


def excel_safe_sheet_name(name: str) -> str:
    """
    Makes a string safe for use as an Excel worksheet name.
    - Max 31 characters
    - No special characters: / \\ ? * [ ] :
    """
    invalid = ["/", "\\", "?", "*", "[", "]", ":"]
    for char in invalid:
        name = name.replace(char, "_")
    return name[:31]
