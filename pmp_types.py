"""
PenguinMod File Converter - Types
Shared type definitions
"""

from enum import Enum


class ConverterType(Enum):
    """Converter type enumeration matching the three ideas"""
    LEGACY = "legacy"
    IDEA1 = "idea1"
    IDEA2 = "idea2"
    HIDDEN = "hidden"
