"""
Todo management system for SWE Agent
"""

import threading
from typing import Dict
from dataclasses import dataclass


@dataclass
class SubTask:
    """Represents a decomposed subtask"""
    id: str
    description: str
    tools_needed: list
    expected_output: str
    verification_criteria: str
    priority: int = 1
    status: str = "pending"  # pending, in_progress, completed, failed


class TodoManager:
    """Manages and displays todo list updates to users"""
    
    def __init__(self, show_updates: bool = True):
        self.show_updates = show_updates
        self.todos = []
        self.lock = threading.Lock()
    
    def update_todo(self, todo_id: str, status: str, description: str = None):
        """Update a todo item and optionally display to user"""
        with self.lock:
            for todo in self.todos:
                if todo.get('id') == todo_id:
                    todo['status'] = status
                    if description:
                        todo['description'] = description
                    break
            else:
                # Add new todo if not found
                self.todos.append({
                    'id': todo_id,
                    'status': status,
                    'description': description or f"Task {todo_id}"
                })
        
        if self.show_updates:
            self._display_todo_update(todo_id, status, description)
    
    def _display_todo_update(self, todo_id: str, status: str, description: str):
        """Display todo update to user"""
        status_icons = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌',
            'paused': '⏸️'
        }
        
        icon = status_icons.get(status, '📝')
        print(f"\n{icon} Todo Update: {description[:60]}{'...' if len(description) > 60 else ''} [{status.upper()}]")
    
    def get_status_summary(self) -> Dict[str, int]:
        """Get summary of todo statuses"""
        with self.lock:
            summary = {}
            for todo in self.todos:
                status = todo.get('status', 'unknown')
                summary[status] = summary.get(status, 0) + 1
            return summary
    
    def display_full_list(self):
        """Display complete todo list"""
        with self.lock:
            if not self.todos:
                print("\n📝 No todos currently tracked")
                return
            
            print("\n📝 Current Todo List:")
            for i, todo in enumerate(self.todos, 1):
                status = todo.get('status', 'unknown')
                desc = todo.get('description', 'No description')
                status_icons = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'failed': '❌', 'paused': '⏸️'}
                icon = status_icons.get(status, '📝')
                print(f"  {i}. {icon} {desc} [{status.upper()}]")