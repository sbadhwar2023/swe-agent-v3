"""
SWE Agent - Software Engineering Agent

A powerful task execution system using LangGraph for planning, decomposition, and execution.
"""

from .agent import LangGraphTaskAgent
from .config import UserConfig
from .permissions import PermissionManager
from .todos import TodoManager

__version__ = "1.0.0"
__all__ = ["LangGraphTaskAgent", "UserConfig", "PermissionManager", "TodoManager"]