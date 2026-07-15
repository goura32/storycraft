"""Storycraft: LLMで日本語小説シリーズを最後まで書き切る道具。"""

__version__ = "0.1.0"

from .config import Settings
from .log import logger

__all__ = ["Settings", "logger"]
