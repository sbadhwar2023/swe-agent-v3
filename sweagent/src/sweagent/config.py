"""
Configuration management for SWE Agent
"""

import json
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class UserConfig:
    """Configuration for user requests and system behavior"""
    task_description: str = ""
    interactive_mode: bool = True
    permission_level: str = "elevated"  # safe, elevated, admin
    auto_approve_safe_operations: bool = True
    show_todo_updates: bool = True
    max_iterations: int = 10
    output_format: str = "detailed"  # minimal, standard, detailed
    working_directory: str = "."
    allowed_file_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_file_patterns is None:
            self.allowed_file_patterns = ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]


def load_config_from_file(config_path: str) -> UserConfig:
    """Load configuration from YAML or JSON file"""
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"⚠️ Config file not found: {config_path}. Using defaults.")
        return UserConfig()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Create UserConfig with loaded data
        config = UserConfig()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    except Exception as e:
        print(f"⚠️ Error loading config file: {e}. Using defaults.")
        return UserConfig()


def create_sample_config(output_path: str):
    """Create a sample configuration file"""
    sample_config = {
        "task_description": "Analyze the codebase and provide improvement suggestions",
        "interactive_mode": True,
        "permission_level": "elevated",
        "auto_approve_safe_operations": True,
        "show_todo_updates": True,
        "max_iterations": 10,
        "output_format": "detailed",
        "working_directory": ".",
        "allowed_file_patterns": ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            if output_path.endswith(('.yaml', '.yml')):
                yaml.dump(sample_config, f, default_flow_style=False, indent=2)
            else:
                json.dump(sample_config, f, indent=2)
        
        print(f"✅ Sample configuration created at: {output_path}")
    except Exception as e:
        print(f"❌ Error creating sample config: {e}")