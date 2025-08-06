"""
Advanced intelligent tools - Real implementations, not dummies
"""

import os
import json
import threading
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool


@dataclass
class Todo:
    """Todo item with full state tracking"""
    id: str
    content: str
    status: str  # pending, in_progress, completed, failed
    priority: str  # high, medium, low
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TodoManager:
    """Intelligent todo management with persistence"""
    
    def __init__(self):
        self.todos: Dict[str, Todo] = {}
        self.lock = threading.Lock()
        self.listeners = []  # For real-time updates
    
    def add_listener(self, callback):
        """Add listener for todo updates"""
        self.listeners.append(callback)
    
    def _notify_listeners(self, todo: Todo, action: str):
        """Notify all listeners of changes"""
        for listener in self.listeners:
            try:
                listener(todo, action)
            except:
                pass  # Don't let listener errors break todo management
    
    def update_todos(self, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update multiple todos atomically"""
        with self.lock:
            updated = []
            errors = []
            
            for todo_data in todos:
                try:
                    # Validate required fields
                    required = ['id', 'content', 'status', 'priority']
                    if not all(field in todo_data for field in required):
                        errors.append(f"Missing required fields for todo: {todo_data}")
                        continue
                    
                    # Validate status and priority
                    valid_status = ['pending', 'in_progress', 'completed', 'failed']
                    valid_priority = ['high', 'medium', 'low']
                    
                    if todo_data['status'] not in valid_status:
                        errors.append(f"Invalid status '{todo_data['status']}' for todo {todo_data['id']}")
                        continue
                        
                    if todo_data['priority'] not in valid_priority:
                        errors.append(f"Invalid priority '{todo_data['priority']}' for todo {todo_data['id']}")
                        continue
                    
                    # Create or update todo
                    todo_id = todo_data['id']
                    import datetime
                    now = datetime.datetime.now().isoformat()
                    
                    if todo_id in self.todos:
                        # Update existing
                        todo = self.todos[todo_id]
                        todo.content = todo_data['content']
                        todo.status = todo_data['status']
                        todo.priority = todo_data['priority']
                        todo.updated_at = now
                        todo.metadata.update(todo_data.get('metadata', {}))
                        action = 'updated'
                    else:
                        # Create new
                        todo = Todo(
                            id=todo_id,
                            content=todo_data['content'],
                            status=todo_data['status'],
                            priority=todo_data['priority'],
                            created_at=now,
                            updated_at=now,
                            metadata=todo_data.get('metadata', {})
                        )
                        self.todos[todo_id] = todo
                        action = 'created'
                    
                    updated.append(asdict(todo))
                    self._notify_listeners(todo, action)
                    
                except Exception as e:
                    errors.append(f"Error processing todo {todo_data.get('id', 'unknown')}: {str(e)}")
            
            # Generate summary
            status_counts = {}
            for todo in self.todos.values():
                status_counts[todo.status] = status_counts.get(todo.status, 0) + 1
            
            return {
                "success": len(errors) == 0,
                "updated_todos": len(updated),
                "total_todos": len(self.todos),
                "status_summary": status_counts,
                "errors": errors,
                "todos": updated
            }
    
    def get_all_todos(self) -> List[Dict[str, Any]]:
        """Get all todos"""
        with self.lock:
            return [asdict(todo) for todo in self.todos.values()]
    
    def get_todos_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get todos by status"""
        with self.lock:
            return [asdict(todo) for todo in self.todos.values() if todo.status == status]


# Global todo manager instance
_todo_manager = TodoManager()


@tool
def todo_write(todos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create and track task lists for complex work - Claude Code equivalent"""
    try:
        result = _todo_manager.update_todos(todos)
        
        # Add helpful display for user
        if result['success']:
            print(f"✅ Updated {result['updated_todos']} todos")
            for status, count in result['status_summary'].items():
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'failed': '❌'}
                print(f"   {status_emoji.get(status, '📝')} {status}: {count}")
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Todo management failed: {str(e)}"}


class SubAgent:
    """Intelligent sub-agent that can work autonomously"""
    
    def __init__(self, api_key: str, agent_type: str = "general"):
        self.api_key = api_key
        self.agent_type = agent_type
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0
        )
        
        # Sub-agent has access to basic tools
        from .tools import read_file, write_file, edit_file, glob_files, ls_directory, grep_search, bash_command
        self.tools = [read_file, write_file, edit_file, glob_files, ls_directory, grep_search, bash_command]
    
    def execute_task(self, description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute task autonomously with intelligence"""
        context = context or {}
        
        # Create specialized system prompt based on agent type
        system_prompts = {
            "search": """You are a specialized search agent. Your job is to find information efficiently.
            Focus on using grep_search, glob_files, and read_file tools to locate what the user needs.
            Be thorough but efficient. Return precise results.""",
            
            "analysis": """You are a code analysis agent. Examine code quality, structure, and issues.
            Use read_file, grep_search to understand codebases. Provide detailed technical insights.
            Look for patterns, bugs, optimizations, and architectural issues.""",
            
            "modification": """You are a code modification agent. Make precise changes to existing code.
            Use read_file to understand context, then edit_file or multi_edit to make changes.
            Always verify changes make sense and don't break functionality.""",
            
            "creation": """You are a code creation agent. Build new files and project structures.
            Use write_file and bash_command to create comprehensive solutions.
            Follow best practices and create production-quality code.""",
            
            "general": """You are a general purpose agent. Analyze the task and use appropriate tools.
            Be intelligent about tool selection and work systematically."""
        }
        
        system_prompt = system_prompts.get(self.agent_type, system_prompts["general"])
        
        prompt = f"""{system_prompt}

TASK: {description}
CONTEXT: {json.dumps(context, indent=2)}

Available tools: {[tool.name for tool in self.tools]}

Execute this task completely and intelligently. Use multiple tools if needed.
Provide a detailed report of what you accomplished."""

        try:
            # Execute with tool calling
            messages = [HumanMessage(content=prompt)]
            response = self.llm.bind_tools(self.tools).invoke(messages)
            
            # Handle tool calls
            tool_results = []
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # Find and execute tool
                    tool_func = next((t for t in self.tools if t.name == tool_name), None)
                    if tool_func:
                        result = tool_func.invoke(tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result
                        })
                
                # Get final response after tool execution
                from langchain_core.messages import ToolMessage
                for i, tool_call in enumerate(response.tool_calls):
                    messages.append(ToolMessage(
                        content=json.dumps(tool_results[i]['result']),
                        tool_call_id=tool_call['id']
                    ))
                
                final_response = self.llm.invoke(messages)
                
                return {
                    "success": True,
                    "agent_type": self.agent_type,
                    "task": description,
                    "tool_calls": len(response.tool_calls),
                    "tool_results": tool_results,
                    "response": final_response.content,
                    "context": context
                }
            else:
                return {
                    "success": True,
                    "agent_type": self.agent_type,
                    "task": description,
                    "tool_calls": 0,
                    "response": response.content,
                    "context": context
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Sub-agent execution failed: {str(e)}",
                "agent_type": self.agent_type,
                "task": description
            }


@tool
def task_agent(description: str, agent_type: str = "general", context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Launch specialized agents for focused work - Real implementation"""
    try:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"success": False, "error": "ANTHROPIC_API_KEY not found"}
        
        # Validate agent type
        valid_types = ["search", "analysis", "modification", "creation", "general"]
        if agent_type not in valid_types:
            return {"success": False, "error": f"Invalid agent type. Must be one of: {valid_types}"}
        
        print(f"🤖 Spawning {agent_type} sub-agent for: {description[:50]}...")
        
        # Create and execute sub-agent
        sub_agent = SubAgent(api_key, agent_type)
        result = sub_agent.execute_task(description, context)
        
        if result['success']:
            print(f"✅ Sub-agent completed with {result['tool_calls']} tool calls")
        else:
            print(f"❌ Sub-agent failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Sub-agent spawn failed: {str(e)}"}


# Export for easy import
__all__ = ['todo_write', 'task_agent', 'TodoManager', 'SubAgent']