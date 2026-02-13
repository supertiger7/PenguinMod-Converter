"""
PenguinMod File Converter - Logging System
Provides structured logging with levels and filtering
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Set


class LogLevel(Enum):
    """Log level enumeration"""
    INFO = 1
    DEBUG = 2
    NOTE = 3
    WARN = 4
    ERROR = 5
    FATAL = 6


@dataclass
class LogEntry:
    """Represents a single log entry"""
    level: LogLevel
    source: str
    message: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
    def __str__(self):
        """Format log entry as string"""
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{self.level.name}][{self.source}] {self.message}"


class LogFilter:
    """Manages log level filtering"""
    
    def __init__(self):
        # By default, show all log levels
        self.enabled_levels: Set[LogLevel] = set(LogLevel)
        
    def set_level(self, level: LogLevel, enabled: bool):
        """Enable or disable a specific log level"""
        if enabled:
            self.enabled_levels.add(level)
        else:
            self.enabled_levels.discard(level)
            
    def is_enabled(self, level: LogLevel) -> bool:
        """Check if a log level is enabled"""
        return level in self.enabled_levels
        
    def should_show(self, entry: LogEntry) -> bool:
        """Check if a log entry should be shown based on current filter"""
        return entry.level in self.enabled_levels
        
    def enable_all(self):
        """Enable all log levels"""
        self.enabled_levels = set(LogLevel)
        
    def disable_all(self):
        """Disable all log levels"""
        self.enabled_levels.clear()
