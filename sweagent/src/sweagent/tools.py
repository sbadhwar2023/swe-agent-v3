"""
Tool definitions for SWE Agent
"""

import os
import glob
import re
import json
import subprocess
import requests
from typing import Dict, List, Any
from langchain_core.tools import tool
from .permissions import PermissionManager
from .todos import TodoManager


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


@tool
def todo_write_tool(todos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Update todo list with new tasks and statuses - equivalent to Claude Code's TodoWrite"""
    try:
        # Validate todo structure
        for todo in todos:
            required_fields = ['id', 'content', 'status', 'priority']
            if not all(field in todo for field in required_fields):
                return {"error": f"Todo missing required fields: {required_fields}"}
            
            if todo['status'] not in ['pending', 'in_progress', 'completed', 'failed']:
                return {"error": f"Invalid status: {todo['status']}"}
                
            if todo['priority'] not in ['high', 'medium', 'low']:
                return {"error": f"Invalid priority: {todo['priority']}"}
        
        # This would integrate with a global todo manager if available
        # For now, return success with todo summary
        status_counts = {}
        for todo in todos:
            status = todo['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "success": True,
            "todos_updated": len(todos),
            "status_summary": status_counts,
            "message": f"Successfully updated {len(todos)} todos"
        }
        
    except Exception as e:
        return {"error": f"Todo update failed: {str(e)}"}


@tool 
def task_delegation_tool(subtask: str, agent_type: str = "general", context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Delegate task to specialized sub-agent - equivalent to Claude Code's task delegation"""
    try:
        context = context or {}
        
        # Simulate sub-agent task delegation
        # In a full implementation, this would spawn actual sub-agents
        
        agent_capabilities = {
            "file_ops": ["read", "write", "edit", "search", "analyze"],
            "web_tasks": ["fetch", "search", "request", "scrape"],
            "code_analysis": ["analyze", "review", "test", "refactor"],
            "general": ["any_task"]
        }
        
        if agent_type not in agent_capabilities:
            return {"error": f"Unknown agent type: {agent_type}"}
        
        # For now, return a simulated delegation result
        return {
            "success": True,
            "subtask": subtask,
            "delegated_to": agent_type,
            "agent_capabilities": agent_capabilities[agent_type],
            "status": "delegated",
            "message": f"Task '{subtask}' delegated to {agent_type} agent",
            "context": context
        }
        
    except Exception as e:
        return {"error": f"Task delegation failed: {str(e)}"}