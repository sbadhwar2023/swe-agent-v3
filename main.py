import uuid
import time
import os
import glob
import re
import json
import subprocess
import requests
import argparse
import yaml
import signal
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable, TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from pathlib import Path
import logging
import anthropic
from dataclasses import dataclass

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
try:
    from langgraph_checkpoint.sqlite import SqliteSaver
except ImportError:
    # Fallback for newer versions
    SqliteSaver = None
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State definition for LangGraph
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    task_description: str
    context: Dict[str, Any]
    subtasks: List[Dict[str, Any]]
    current_subtask: Optional[Dict[str, Any]]
    results: List[Dict[str, Any]]
    final_result: Optional[Dict[str, Any]]
    iteration_count: int
    user_config: Dict[str, Any]
    permission_level: str
    interactive_mode: bool
    paused: bool

@dataclass
class SubTask:
    """Represents a decomposed subtask"""
    id: str
    description: str
    tools_needed: List[str]
    expected_output: str
    verification_criteria: str
    priority: int = 1
    status: str = "pending"  # pending, in_progress, completed, failed

@dataclass
class UserConfig:
    """Configuration for user requests and system behavior"""
    task_description: str = ""
    interactive_mode: bool = True
    permission_level: str = "safe"  # safe, elevated, admin
    auto_approve_safe_operations: bool = True
    show_todo_updates: bool = True
    max_iterations: int = 10
    output_format: str = "detailed"  # minimal, standard, detailed
    working_directory: str = "."
    allowed_file_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_file_patterns is None:
            self.allowed_file_patterns = ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]

class PermissionManager:
    """Manages permissions for file operations and system commands"""
    
    SAFE_COMMANDS = [
        'ls', 'dir', 'pwd', 'whoami', 'date', 'git status', 'git log', 
        'npm list', 'pip list', 'python --version', 'node --version'
    ]
    
    ELEVATED_COMMANDS = [
        'mkdir', 'touch', 'cp', 'mv', 'chmod', 'python', 'node', 
        'npm install', 'pip install', 'pytest', 'flake8', 'black'
    ]
    
    ADMIN_COMMANDS = [
        'rm', 'rmdir', 'sudo', 'su', 'chown', 'systemctl', 'service'
    ]
    
    def __init__(self, permission_level: str = "safe"):
        self.permission_level = permission_level
    
    def check_command_permission(self, command: str) -> Tuple[bool, str]:
        """Check if command is allowed at current permission level"""
        command_lower = command.lower().strip()
        
        if any(command_lower.startswith(safe) for safe in self.SAFE_COMMANDS):
            return True, "safe"
        
        if self.permission_level in ["elevated", "admin"]:
            if any(command_lower.startswith(elevated) for elevated in self.ELEVATED_COMMANDS):
                return True, "elevated"
        
        if self.permission_level == "admin":
            if any(command_lower.startswith(admin) for admin in self.ADMIN_COMMANDS):
                return True, "admin"
        
        return False, f"Command '{command}' requires higher permissions"
    
    def check_file_permission(self, file_path: str, operation: str) -> Tuple[bool, str]:
        """Check if file operation is allowed"""
        path = Path(file_path)
        
        # Check if trying to access system files
        system_paths = ['/etc', '/usr', '/bin', '/sbin', '/var/log']
        if any(str(path).startswith(sys_path) for sys_path in system_paths):
            if self.permission_level != "admin":
                return False, f"Access to system path '{file_path}' requires admin permissions"
        
        # Check file operations
        if operation in ["read"]:
            return True, "read allowed"
        elif operation in ["write", "edit", "create"]:
            if self.permission_level in ["elevated", "admin"]:
                return True, "write allowed"
            else:
                return False, f"Write operation requires elevated permissions"
        elif operation in ["delete"]:
            if self.permission_level == "admin":
                return True, "delete allowed"
            else:
                return False, f"Delete operation requires admin permissions"
        
        return True, "operation allowed"

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

# LangChain Tools Definition
@tool
def file_search_tool(pattern: str, directory: str = ".") -> List[str]:
    """Search for files matching a pattern in a directory"""
    try:
        search_pattern = os.path.join(directory, "**", pattern)
        files = glob.glob(search_pattern, recursive=True)
        return files
    except Exception as e:
        return [f"Error: {str(e)}"]

@tool
def grep_search_tool(pattern: str, file_path: str) -> List[Dict[str, Any]]:
    """Search for text patterns in a file"""
    try:
        matches = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append({
                        'line_number': line_num,
                        'line': line.strip(),
                        'file': file_path
                    })
        return matches
    except Exception as e:
        return [{"error": str(e)}]

@tool
def code_analysis_tool(file_path: str) -> Dict[str, Any]:
    """Analyze code file for metrics and complexity"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*')))
        code_lines = total_lines - blank_lines - comment_lines
        
        # Count functions/methods
        function_pattern = r'def\s+\w+|function\s+\w+|class\s+\w+'
        functions = len(re.findall(function_pattern, content, re.IGNORECASE))
        
        return {
            'file': file_path,
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'functions': functions,
            'complexity_score': code_lines / max(functions, 1)
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def file_writer_tool(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file"""
    try:
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Verify file was written
        if os.path.exists(file_path):
            return {
                'file': file_path,
                'size': len(content),
                'lines': content.count('\n') + 1,
                'status': 'success',
                'directory_created': dir_path if dir_path and not os.path.exists(dir_path) else None
            }
        else:
            return {"error": f"File {file_path} was not created successfully"}
            
    except PermissionError:
        return {"error": f"Permission denied writing to {file_path}"}
    except OSError as e:
        return {"error": f"OS error writing file {file_path}: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error writing {file_path}: {str(e)}"}

@tool
def web_request_tool(url: str, method: str = "GET") -> Dict[str, Any]:
    """Make HTTP requests to check web endpoints"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content_length': len(response.content),
            'url': response.url,
            'success': response.status_code < 400
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def file_read_tool(file_path: str, offset: int = 0, limit: int = -1) -> Dict[str, Any]:
    """Read file contents with optional line range"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]
            
        return {
            'file': file_path,
            'content': ''.join(lines),
            'lines_read': len(lines),
            'total_lines': len(open(file_path, 'r').readlines()) if limit == -1 else 'partial',
            'success': True
        }
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except PermissionError:
        return {"error": f"Permission denied: {file_path}"}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}

@tool
def file_edit_tool(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
    """Edit file by replacing old_string with new_string"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_string not in content:
            return {"error": f"String not found in file: {old_string[:50]}..."}
        
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            'file': file_path,
            'replacements': replacements,
            'old_length': len(content),
            'new_length': len(new_content),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error editing file: {str(e)}"}

@tool
def directory_list_tool(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """List directory contents"""
    try:
        items = []
        for item in os.listdir(path):
            if not show_hidden and item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            items.append({
                'name': item,
                'type': 'directory' if is_dir else 'file',
                'size': size,
                'path': item_path
            })
        
        return {
            'path': path,
            'items': sorted(items, key=lambda x: (x['type'], x['name'])),
            'total_items': len(items),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error listing directory: {str(e)}"}

@tool 
def multi_edit_tool(file_path: str, edits: List[Dict[str, str]]) -> Dict[str, Any]:
    """Apply multiple edits to a file in sequence"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        total_edits = 0
        for edit in edits:
            old_str = edit['old_string']
            new_str = edit['new_string']
            replace_all = edit.get('replace_all', False)
            
            if old_str in content:
                if replace_all:
                    content = content.replace(old_str, new_str)
                    total_edits += content.count(old_str)
                else:
                    content = content.replace(old_str, new_str, 1)
                    total_edits += 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'file': file_path,
            'total_edits': total_edits,
            'edits_applied': len(edits),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error applying multi-edits: {str(e)}"}

def create_permission_aware_bash_tool(permission_manager: PermissionManager):
    """Create a bash tool that checks permissions before execution"""
    @tool
    def bash_tool(command: str, working_dir: str = ".", timeout: int = 60) -> Dict[str, Any]:
        """Execute bash commands with permission checking and better error handling"""
        try:
            # Check permissions
            allowed, message = permission_manager.check_command_permission(command)
            if not allowed:
                return {"error": f"Permission denied: {message}"}
            
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=working_dir,
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            return {
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0,
                'working_dir': working_dir,
                'permission_level': message
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command '{command}' timed out after {timeout} seconds"}
        except Exception as e:
            return {"error": f"Command execution failed: {str(e)}"}
    
    return bash_tool

def create_permission_aware_file_tools(permission_manager: PermissionManager):
    """Create file tools that check permissions before operations"""
    
    @tool
    def file_writer_tool(file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file with permission checking"""
        try:
            # Check permissions
            allowed, message = permission_manager.check_file_permission(file_path, "create")
            if not allowed:
                return {"error": f"Permission denied: {message}"}
            
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # Verify file was written
            if os.path.exists(file_path):
                return {
                    'file': file_path,
                    'size': len(content),
                    'lines': content.count('\n') + 1,
                    'status': 'success',
                    'permission_level': message,
                    'directory_created': dir_path if dir_path and not os.path.exists(dir_path) else None
                }
            else:
                return {"error": f"File {file_path} was not created successfully"}
                
        except PermissionError:
            return {"error": f"Permission denied writing to {file_path}"}
        except OSError as e:
            return {"error": f"OS error writing file {file_path}: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error writing {file_path}: {str(e)}"}
    
    @tool
    def file_edit_tool(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
        """Edit file by replacing old_string with new_string with permission checking"""
        try:
            # Check permissions
            allowed, message = permission_manager.check_file_permission(file_path, "edit")
            if not allowed:
                return {"error": f"Permission denied: {message}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_string not in content:
                return {"error": f"String not found in file: {old_string[:50]}..."}
            
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                'file': file_path,
                'replacements': replacements,
                'old_length': len(content),
                'new_length': len(new_content),
                'success': True,
                'permission_level': message
            }
        except Exception as e:
            return {"error": f"Error editing file: {str(e)}"}
    
    return file_writer_tool, file_edit_tool

@tool
def bash_tool(command: str, working_dir: str = ".", timeout: int = 60) -> Dict[str, Any]:
    """Execute bash commands with better error handling (fallback version)"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=working_dir,
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0,
            'working_dir': working_dir
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command '{command}' timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}

@tool
def system_command_tool(command: str, working_dir: str = ".") -> Dict[str, Any]:
    """Execute safe system commands (deprecated - use bash_tool)"""
    try:
        safe_commands = ['ls', 'dir', 'pwd', 'whoami', 'date', 'git status', 'git log', 'npm list', 'pip list', 'mkdir', 'touch', 'cp', 'mv', 'rm -f', 'chmod', 'python', 'node', 'flask run', 'npm', 'pip', 'pytest', 'flake8', 'black']
        if not any(command.startswith(safe_cmd) for safe_cmd in safe_commands):
            return {"error": f"Command not in whitelist: {command}. Use bash_tool for unrestricted commands"}
        
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=working_dir,
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0,
            'working_dir': working_dir
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command '{command}' timed out after 60 seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}

class LangGraphTaskAgent:
    """LangGraph-based multi-agent task system with external configuration and permission management"""
    
    def __init__(self, anthropic_api_key: str, config: UserConfig = None):
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=anthropic_api_key,
            temperature=0
        )
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        
        # Initialize user configuration
        self.config = config or UserConfig()
        self.permission_manager = PermissionManager(self.config.permission_level)
        self.todo_manager = TodoManager(self.config.show_todo_updates)
        self.paused = False
        self.stop_requested = False
        
        # Setup signal handlers for interruption
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
        
        # Create permission-aware tools
        permission_aware_bash = create_permission_aware_bash_tool(self.permission_manager)
        permission_aware_writer, permission_aware_editor = create_permission_aware_file_tools(self.permission_manager)
        
        # Define available tools
        self.tools = [
            file_search_tool,
            file_read_tool,
            permission_aware_editor,  # Use permission-aware version
            permission_aware_writer,  # Use permission-aware version
            multi_edit_tool,
            directory_list_tool,
            grep_search_tool, 
            code_analysis_tool,
            web_request_tool,
            permission_aware_bash,  # Use permission-aware version
            system_command_tool
        ]
        
        self.tool_executor = ToolNode(self.tools)
        
        # Create the graph
        self.workflow = self._create_workflow()
        
        # Add memory with SQLite checkpointer
        if SqliteSaver:
            memory = SqliteSaver.from_conn_string(":memory:")
            self.app = self.workflow.compile(checkpointer=memory)
        else:
            # Run without checkpointer for newer versions
            self.app = self.workflow.compile()
    
    def _handle_interrupt(self, signum, frame):
        """Handle user interruption (Ctrl+C)"""
        print(f"\n🛑 Interruption received (signal {signum})")
        
        if self.config.interactive_mode:
            print("\nOptions:")
            print("1. Pause execution (resume later)")
            print("2. Stop execution")
            print("3. Continue execution")
            
            try:
                choice = input("Enter choice (1-3): ").strip()
                if choice == "1":
                    self.paused = True
                    self.todo_manager.update_todo("main_task", "paused", "Execution paused by user")
                    print("⏸️ Execution paused. Use resume_execution() to continue.")
                elif choice == "2":
                    self.stop_requested = True
                    print("🛑 Stop requested. Execution will halt gracefully.")
                elif choice == "3":
                    print("▶️ Continuing execution...")
                else:
                    print("Invalid choice. Continuing execution...")
            except (EOFError, KeyboardInterrupt):
                self.stop_requested = True
                print("\n🛑 Force stop requested.")
        else:
            self.stop_requested = True
            print("🛑 Non-interactive mode: stopping execution.")
    
    def pause_execution(self):
        """Pause execution programmatically"""
        self.paused = True
        self.todo_manager.update_todo("main_task", "paused", "Execution paused programmatically")
        print("⏸️ Execution paused.")
    
    def resume_execution(self):
        """Resume paused execution"""
        self.paused = False
        self.todo_manager.update_todo("main_task", "in_progress", "Execution resumed")
        print("▶️ Execution resumed.")
    
    def stop_execution(self):
        """Stop execution programmatically"""
        self.stop_requested = True
        print("🛑 Stop requested.")
    
    def _check_permissions_and_approve(self, operation: str, target: str, operation_type: str) -> bool:
        """Check permissions and get user approval if needed"""
        if operation_type == "command":
            allowed, message = self.permission_manager.check_command_permission(target)
        elif operation_type == "file":
            allowed, message = self.permission_manager.check_file_permission(target, operation)
        else:
            return True  # Unknown operation type, allow by default
        
        if not allowed:
            if self.config.interactive_mode:
                print(f"⚠️ Permission required: {message}")
                print(f"Operation: {operation} on {target}")
                approval = input("Approve this operation? (y/N): ").strip().lower()
                return approval in ['y', 'yes']
            else:
                print(f"❌ Operation denied: {message}")
                return False
        
        # For safe operations, auto-approve if configured
        if self.config.auto_approve_safe_operations and "safe" in message:
            return True
        
        # For elevated operations in interactive mode, ask for approval
        if self.config.interactive_mode and operation_type in ["elevated", "admin"]:
            print(f"🔐 {operation} requires {operation_type} permissions")
            approval = input("Approve this operation? (y/N): ").strip().lower()
            return approval in ['y', 'yes']
        
        return True
    
    def _wait_if_paused(self):
        """Wait while execution is paused"""
        while self.paused and not self.stop_requested:
            time.sleep(0.5)
        
        if self.stop_requested:
            raise KeyboardInterrupt("Execution stopped by user request")
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("decomposer", self._decomposer_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("aggregator", self._aggregator_node)
        
        # Define edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "decomposer")
        workflow.add_edge("decomposer", "executor")
        workflow.add_conditional_edges(
            "executor",
            self._should_continue,
            {
                "continue": "executor",
                "aggregate": "aggregator"
            }
        )
        workflow.add_edge("aggregator", END)
        
        return workflow
    
    def _throttle_request(self):
        """Throttle API requests to prevent rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            print(f"   ⏱️ Throttling request: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Plan the overall approach for the task"""
        print(f"\n📋 Task: {state['task_description']}")
        print("🔄 Planning phase started...")
        logger.info("🔄 Planning phase started")
        
        planning_prompt = f"""
        Analyze this task and create an execution plan:
        
        Task: {state['task_description']}
        Context: {json.dumps(state['context'], indent=2)}
        
        Available tools: {[tool.name for tool in self.tools]}
        
        Create a high-level execution strategy. Consider:
        1. What information do we need to gather?
        2. What tools will be most useful?
        3. What are the key success criteria?
        4. How should we break this down?
        
        Provide your analysis as a structured plan.
        """
        
        messages = state["messages"] + [HumanMessage(content=planning_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        new_state = state.copy()
        new_state["messages"] = messages + [response]
        
        print("✅ Planning phase completed")
        logger.info("✅ Planning phase completed")
        return new_state
    
    def _decomposer_node(self, state: AgentState) -> AgentState:
        """Decompose the task into specific subtasks"""
        print("🔄 Breaking down into subtasks...")
        logger.info("🔄 Decomposition phase started")
        
        decomposition_prompt = f"""
        Analyze this task and determine if it needs decomposition:

        Task: {state['task_description']}
        Context: {json.dumps(state['context'], indent=2)}
        Available tools: {[tool.name for tool in self.tools]}

        CRITICAL: Only decompose if the task genuinely requires multiple distinct steps or tools.

        For SIMPLE tasks that can be completed with a single tool call (like "list files", "read file", "search for X"):
        - Create just ONE subtask that directly uses the appropriate tool
        - Don't artificially break down simple operations into verification steps

        For COMPLEX tasks requiring multiple operations (like "create a web app", "analyze and refactor code"):
        - Break into logical subtasks that each accomplish something meaningful

        Examples:
        - "list files" → ONE subtask using directory_list_tool
        - "read main.py" → ONE subtask using file_read_tool  
        - "create a Flask app with authentication" → Multiple subtasks (setup, routes, auth, etc.)

        Format your response as JSON:
        {{
            "subtasks": [
                {{
                    "id": "unique_id",
                    "description": "specific task description",
                    "tools_needed": ["tool_name1", "tool_name2"],
                    "expected_output": "what should be produced",
                    "verification_criteria": "how to check success",
                    "priority": 1
                }}
            ]
        }}

        Remember: Prefer fewer, meaningful subtasks over many trivial ones.
        """
        
        messages = state["messages"] + [HumanMessage(content=decomposition_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        # Parse the subtasks
        try:
            subtasks_data = json.loads(response.content)
            subtasks = []
            for task_data in subtasks_data["subtasks"]:
                subtask = SubTask(
                    id=task_data["id"],
                    description=task_data["description"],
                    tools_needed=task_data["tools_needed"],
                    expected_output=task_data["expected_output"],
                    verification_criteria=task_data["verification_criteria"],
                    priority=task_data.get("priority", 3)
                )
                subtasks.append(subtask.__dict__)
            
            # Sort by priority
            subtasks.sort(key=lambda x: x["priority"])
            
        except Exception as e:
            logger.error(f"Failed to parse subtasks: {e}")
            # Fallback single subtask
            subtasks = [{
                "id": "fallback_task",
                "description": state['task_description'],
                "tools_needed": ["file_search_tool"],
                "expected_output": "Task completion",
                "verification_criteria": "Task executed without errors",
                "priority": 1,
                "status": "pending"
            }]
        
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [response]
        new_state["subtasks"] = subtasks
        new_state["results"] = []
        new_state["iteration_count"] = 0
        
        print(f"✅ Created {len(subtasks)} subtasks:")
        for i, task in enumerate(subtasks, 1):
            print(f"   {i}. {task['description'][:60]}{'...' if len(task['description']) > 60 else ''}")
        logger.info(f"✅ Decomposed into {len(subtasks)} subtasks")
        return new_state
    
    def _executor_node(self, state: AgentState) -> AgentState:
        """Execute and verify the current subtask in a single API call"""
        self._wait_if_paused()  # Check if paused
        logger.info("🔄 Execution phase started")
        
        # Get next pending subtask
        current_subtask = None
        for subtask in state["subtasks"]:
            if subtask["status"] == "pending":
                current_subtask = subtask
                break
        
        if not current_subtask:
            logger.info("No more subtasks to execute")
            new_state = state.copy()
            return new_state
        
        current_subtask["status"] = "in_progress"
        
        # Update todo manager
        self.todo_manager.update_todo(
            current_subtask["id"], 
            "in_progress", 
            current_subtask["description"]
        )
        
        print(f"\n🔧 Executing: {current_subtask['description']}")
        
        execution_prompt = f"""
        Execute this specific subtask using the available tools. DO NOT just check if files exist - actually create/modify what is needed:
        
        Subtask: {current_subtask['description']}
        Tools needed: {current_subtask['tools_needed']}
        Expected output: {current_subtask['expected_output']}
        Verification criteria: {current_subtask['verification_criteria']}
        Context: {json.dumps(state['context'], indent=2)}
        
        IMPORTANT EXECUTION STEPS:
        1. ACTUALLY DO THE WORK - create files, install packages, etc. using the appropriate tools
        2. Use file_writer_tool to create new files, not just file_read_tool to check them
        3. Use bash_tool for installations, running commands, testing functionality
        4. Only mark as COMPLETED if you actually created/modified something concrete
        5. Provide specific evidence of what was created/done
        
        For file creation tasks:
        - Use file_writer_tool with the actual file content
        - Use directory_list_tool to verify files were created
        
        For installations:
        - Use bash_tool to run pip install, npm install, etc.
        
        Be specific about tool parameters and provide concrete outputs showing what was accomplished.
        """
        
        messages = state["messages"] + [HumanMessage(content=execution_prompt)]
        
        # Execute with tool calling
        try:
            self._throttle_request()
            response = self.llm.bind_tools(self.tools).invoke(messages)
            messages.append(response)
            
            # Execute any tool calls
            if response.tool_calls:
                print(f"   🔧 Using tools: {[call['name'] for call in response.tool_calls]}")
                tool_result = self.tool_executor.invoke({"messages": [response]})
                if "messages" in tool_result:
                    # Add all tool result messages immediately after the tool use message
                    for tool_msg in tool_result["messages"]:
                        messages.append(tool_msg)
            
            # Get final response with verification
            self._throttle_request()
            final_response = self.llm.invoke(messages)
            messages.append(final_response)
            
        except Exception as e:
            print(f"   ⚠️ Execution error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
            final_response = AIMessage(content=f"Task execution encountered an error: {str(e)}")
            messages.append(final_response)
        
        # Store result with better verification
        response_content = str(final_response.content).lower() if final_response.content else ""
        
        # More strict success detection - require concrete evidence of work done
        concrete_success_indicators = [
            "file created", "successfully created", "successfully written",
            "installed successfully", "server started", "directory created",
            "successfully executed", "file written", "command completed"
        ]
        error_indicators = ["error", "failed", "exception", "traceback", "not found", "permission denied"]
        
        # Check if actual tool results show success
        tool_success = False
        if hasattr(final_response, 'tool_calls') and final_response.tool_calls:
            # If tools were called, check their results in the messages
            for msg in messages[-5:]:  # Check recent messages for tool results
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    msg_content = str(msg.content).lower()
                    if any(indicator in msg_content for indicator in ["success", "created", "written", "installed"]):
                        if "error" not in msg_content:
                            tool_success = True
                            break
        
        has_concrete_success = any(indicator in response_content for indicator in concrete_success_indicators)
        has_error = any(indicator in response_content for indicator in error_indicators)
        
        # Require concrete evidence of work done
        success = (has_concrete_success or tool_success) and not has_error
        
        result = {
            "subtask_id": current_subtask["id"],
            "subtask_description": current_subtask["description"],
            "execution_messages": [msg.content for msg in messages[-3:]],
            "success": success,
            "output": final_response.content,
            "verified": True
        }
        
        current_subtask["status"] = "completed" if result["success"] else "failed"
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} Task {'completed' if result['success'] else 'failed'}: {current_subtask['description'][:50]}{'...' if len(current_subtask['description']) > 50 else ''}")
        
        # Update todo manager
        self.todo_manager.update_todo(
            current_subtask["id"], 
            "completed" if result["success"] else "failed", 
            current_subtask["description"]
        )
        
        new_state = state.copy()
        new_state["messages"] = messages
        new_state["current_subtask"] = current_subtask
        new_state["results"].append(result)
        new_state["iteration_count"] += 1
        
        logger.info(f"✅ Executed subtask: {current_subtask['description'][:50]}...")
        return new_state
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue executing subtasks or aggregate results"""
        pending_subtasks = [s for s in state["subtasks"] if s["status"] == "pending"]
        
        if pending_subtasks and state["iteration_count"] < 10:  # Max 10 iterations
            return "continue"
        else:
            return "aggregate"
    
    def _aggregator_node(self, state: AgentState) -> AgentState:
        """Aggregate all results into a final report"""
        completed = len([s for s in state['subtasks'] if s['status'] == 'completed'])
        failed = len([s for s in state['subtasks'] if s['status'] == 'failed'])
        total = len(state['subtasks'])
        
        print(f"\n📊 Task Summary: {completed}/{total} completed, {failed} failed")
        print("📝 Generating final report...")
        logger.info("🔄 Aggregation phase started")
        
        aggregation_prompt = f"""
        Create a comprehensive final report based on all subtask results:
        
        Original Task: {state['task_description']}
        
        Subtasks Completed: {len([s for s in state['subtasks'] if s['status'] == 'completed'])}
        Total Subtasks: {len(state['subtasks'])}
        
        Results Summary:
        {json.dumps(state['results'], indent=2)}
        
        Provide a comprehensive report including:
        1. Executive summary
        2. Key findings
        3. Detailed results for each subtask
        4. Overall success assessment
        5. Recommendations for next steps
        
        Format the report in a clear, structured manner.
        """
        
        # Filter messages carefully to maintain tool_use/tool_result pairing
        valid_messages = []
        for i, msg in enumerate(state["messages"]):
            # Always include tool messages to maintain pairing
            if hasattr(msg, 'type') and msg.type in ['tool', 'tool_result']:
                valid_messages.append(msg)
            # Include messages with actual content
            elif hasattr(msg, 'content') and msg.content and str(msg.content).strip():
                valid_messages.append(msg)
            # Include AI messages with tool calls even if content is empty
            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                valid_messages.append(msg)
        
        messages = valid_messages + [HumanMessage(content=aggregation_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        # Create final result
        final_result = {
            "task_description": state["task_description"],
            "subtasks_total": len(state["subtasks"]),
            "subtasks_completed": len([s for s in state["subtasks"] if s["status"] == "completed"]),
            "subtasks_failed": len([s for s in state["subtasks"] if s["status"] == "failed"]),
            "success_rate": len([r for r in state["results"] if r["success"]]) / max(len(state["results"]), 1),
            "detailed_results": state["results"],
            "final_report": response.content,
            "execution_time": time.time()
        }
        
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [response]
        new_state["final_result"] = final_result
        
        print("✅ Final report generated")
        logger.info("✅ Final aggregation completed")
        return new_state
    
    def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using the LangGraph workflow"""
        
        thread_id = str(uuid.uuid4())
        context = context or {}
        
        # Add main task to todo manager
        self.todo_manager.update_todo("main_task", "in_progress", task_description)
        
        initial_state = {
            "messages": [],
            "task_description": task_description,
            "context": context,
            "subtasks": [],
            "current_subtask": None,
            "results": [],
            "final_result": None,
            "iteration_count": 0,
            "user_config": self.config.__dict__,
            "permission_level": self.config.permission_level,
            "interactive_mode": self.config.interactive_mode,
            "paused": self.paused
        }
        
        print(f"\n🚀 Starting task execution...")
        logger.info(f"🚀 Starting LangGraph task execution: {task_description}")
        
        try:
            # Execute the workflow
            final_state = self.app.invoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}}
            )
            
            print("\n🎉 Task execution completed successfully!")
            logger.info("✅ LangGraph task execution completed successfully")
            
            # Update main task as completed
            self.todo_manager.update_todo("main_task", "completed", task_description)
            
            # Show final todo summary if configured
            if self.config.show_todo_updates:
                summary = self.todo_manager.get_status_summary()
                print(f"\n📊 Final Todo Summary: {summary}")
            
            return final_state["final_result"]
            
        except KeyboardInterrupt:
            print(f"\n⏸️ Task execution interrupted by user")
            self.todo_manager.update_todo("main_task", "paused", f"Task interrupted: {task_description}")
            return {
                "task_description": task_description,
                "success": False,
                "interrupted": True,
                "execution_time": time.time()
            }
        except Exception as e:
            print(f"\n❌ Task execution failed: {str(e)}")
            logger.error(f"❌ LangGraph task execution failed: {e}")
            self.todo_manager.update_todo("main_task", "failed", f"Task failed: {task_description}")
            return {
                "task_description": task_description,
                "success": False,
                "error": str(e),
                "execution_time": time.time()
            }

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
        "permission_level": "safe",
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

def parse_cli_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="LangGraph Multi-Agent Task System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Create a web app"
  python main.py --config config.yaml
  python main.py --interactive --permission elevated "Deploy the application"
  python main.py --create-config config.yaml
        """
    )
    
    parser.add_argument(
        'task', 
        nargs='?', 
        help='Task description to execute'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    
    parser.add_argument(
        '--create-config',
        type=str,
        metavar='PATH',
        help='Create a sample configuration file'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enable interactive mode'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Disable interactive mode'
    )
    
    parser.add_argument(
        '--permission',
        choices=['safe', 'elevated', 'admin'],
        help='Set permission level'
    )
    
    parser.add_argument(
        '--show-todos',
        action='store_true',
        help='Show todo list updates'
    )
    
    parser.add_argument(
        '--hide-todos',
        action='store_true',
        help='Hide todo list updates'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['minimal', 'standard', 'detailed'],
        help='Set output format'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        help='Maximum number of iterations'
    )
    
    parser.add_argument(
        '--working-dir',
        type=str,
        help='Working directory for operations'
    )
    
    return parser.parse_args()

def main():
    """Main CLI entry point"""
    args = parse_cli_arguments()
    
    # Handle config file creation
    if args.create_config:
        create_sample_config(args.create_config)
        return
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = UserConfig()
    
    # Override config with CLI arguments
    if args.interactive:
        config.interactive_mode = True
    elif args.non_interactive:
        config.interactive_mode = False
    
    if args.permission:
        config.permission_level = args.permission
    
    if args.show_todos:
        config.show_todo_updates = True
    elif args.hide_todos:
        config.show_todo_updates = False
    
    if args.output_format:
        config.output_format = args.output_format
    
    if args.max_iterations:
        config.max_iterations = args.max_iterations
    
    if args.working_dir:
        config.working_directory = args.working_dir
        os.chdir(args.working_dir)
    
    # Get task description
    if args.task:
        config.task_description = args.task
    elif not config.task_description:
        if config.interactive_mode:
            config.task_description = input("Enter task description: ").strip()
            if not config.task_description:
                print("❌ No task description provided.")
                return
        else:
            print("❌ No task description provided. Use --task or configure in config file.")
            return
    
    # Initialize API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Display configuration
    print("🚀 LangGraph Multi-Agent Task System")
    print(f"📋 Task: {config.task_description}")
    print(f"🔐 Permission Level: {config.permission_level}")
    print(f"🎛️  Interactive Mode: {'Yes' if config.interactive_mode else 'No'}")
    print(f"📝 Todo Updates: {'Enabled' if config.show_todo_updates else 'Disabled'}")
    print(f"📁 Working Directory: {config.working_directory}")
    
    # Create and configure agent
    try:
        agent = LangGraphTaskAgent(api_key, config)
        
        # Execute task
        result = agent.execute_task(
            config.task_description,
            context={
                "working_directory": config.working_directory,
                "permission_level": config.permission_level,
                "interactive_mode": config.interactive_mode
            }
        )
        
        # Display results based on output format
        if config.output_format == "minimal":
            success = result.get('success_rate', 0) > 0.5
            print(f"\n{'✅' if success else '❌'} Task {'completed' if success else 'failed'}")
        elif config.output_format == "standard": 
            print(f"\n📊 Results:")
            print(f"Success Rate: {result.get('success_rate', 0):.1%}")
            print(f"Subtasks: {result.get('subtasks_completed', 0)}/{result.get('subtasks_total', 0)}")
        else:  # detailed
            print(f"\n📊 Detailed Results:")
            print(f"Success Rate: {result.get('success_rate', 0):.1%}")
            print(f"Subtasks: {result.get('subtasks_completed', 0)}/{result.get('subtasks_total', 0)}")
            if result.get('final_report'):
                print(f"\n📄 Final Report:\n{result['final_report']}")
        
        # Show todo summary
        if config.show_todo_updates:
            agent.todo_manager.display_full_list()
    
    except KeyboardInterrupt:
        print("\n👋 Execution interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error in main: {e}")

if __name__ == "__main__":
    main()
