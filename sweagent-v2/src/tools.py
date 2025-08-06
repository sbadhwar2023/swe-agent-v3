"""
Complete tool set - Claude Code equivalent implementations
"""

import os
import json
import subprocess
import glob
import re
import fnmatch
from typing import Dict, List, Any, Optional
from pathlib import Path
from langchain_core.tools import tool


@tool
def read_file(file_path: str, offset: int = 0, limit: int = -1) -> Dict[str, Any]:
    """Read file contents with optional line range - Claude Code equivalent"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        original_total = len(lines)
        
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]
            
        return {
            "success": True,
            "file": file_path,
            "content": ''.join(lines),
            "lines_read": len(lines),
            "total_lines": original_total,
            "offset": offset,
            "limit": limit if limit > 0 else "all"
        }
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"Error reading file: {str(e)}"}


@tool
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Create new files - Claude Code equivalent"""
    try:
        # Create directory if needed
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        # Check if file already exists
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "file": file_path,
            "size": len(content),
            "lines": content.count('\n') + 1,
            "created": not file_exists,
            "overwritten": file_exists,
            "message": f"{'Created' if not file_exists else 'Overwrote'} {file_path} with {len(content)} characters"
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied writing to {file_path}"}
    except OSError as e:
        return {"success": False, "error": f"OS error writing file {file_path}: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error writing file: {str(e)}"}


@tool
def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
    """Edit existing files by replacing text - Claude Code equivalent"""
    try:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        if old_string not in content:
            return {"success": False, "error": f"String not found in file: {old_string[:100]}{'...' if len(old_string) > 100 else ''}"}
        
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1
        
        # Only write if content actually changed
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return {
            "success": True,
            "file": file_path,
            "replacements": replacements,
            "old_length": len(original_content),
            "new_length": len(new_content),
            "characters_changed": len(new_content) - len(original_content),
            "replace_all": replace_all
        }
    except Exception as e:
        return {"success": False, "error": f"Error editing file: {str(e)}"}


@tool
def multi_edit(file_path: str, edits: List[Dict[str, str]]) -> Dict[str, Any]:
    """Apply multiple edits to a file atomically - Claude Code equivalent"""
    try:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        total_replacements = 0
        edit_details = []
        
        for i, edit in enumerate(edits):
            if 'old_string' not in edit or 'new_string' not in edit:
                return {"success": False, "error": f"Edit {i} missing old_string or new_string"}
            
            old_str = edit['old_string']
            new_str = edit['new_string']
            replace_all = edit.get('replace_all', False)
            
            if old_str in content:
                if replace_all:
                    replacements = content.count(old_str)
                    content = content.replace(old_str, new_str)
                else:
                    replacements = 1 if old_str in content else 0
                    content = content.replace(old_str, new_str, 1)
                
                total_replacements += replacements
                edit_details.append({
                    "edit_index": i,
                    "replacements": replacements,
                    "old_string": old_str[:50] + ("..." if len(old_str) > 50 else ""),
                    "new_string": new_str[:50] + ("..." if len(new_str) > 50 else "")
                })
            else:
                edit_details.append({
                    "edit_index": i,
                    "replacements": 0,
                    "error": f"String not found: {old_str[:50]}..."
                })
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return {
            "success": True,
            "file": file_path,
            "total_edits": len(edits),
            "total_replacements": total_replacements,
            "edit_details": edit_details,
            "content_changed": content != original_content,
            "old_length": len(original_content),
            "new_length": len(content)
        }
    except Exception as e:
        return {"success": False, "error": f"Error applying multi-edits: {str(e)}"}


@tool
def glob_files(pattern: str, path: str = ".", sort_by_time: bool = True) -> Dict[str, Any]:
    """Advanced file pattern matching - Claude Code equivalent"""
    try:
        # Handle different pattern formats
        if os.path.isabs(pattern):
            search_pattern = pattern
        elif path == ".":
            search_pattern = os.path.join("**", pattern)
        else:
            search_pattern = os.path.join(path, "**", pattern)
        
        # Get files
        files = glob.glob(search_pattern, recursive=True)
        
        # Filter to only files (not directories)
        files = [f for f in files if os.path.isfile(f)]
        
        # Sort by modification time or alphabetically
        if sort_by_time and files:
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        else:
            files.sort()
        
        # Get file info
        file_info = []
        for file in files:
            try:
                stat = os.stat(file)
                file_info.append({
                    "path": file,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "absolute_path": os.path.abspath(file)
                })
            except:
                file_info.append({
                    "path": file,
                    "absolute_path": os.path.abspath(file)
                })
        
        return {
            "success": True,
            "pattern": pattern,
            "search_path": path,
            "files": files,
            "file_info": file_info,
            "count": len(files),
            "sorted_by_time": sort_by_time
        }
    except Exception as e:
        return {"success": False, "error": f"Error globbing files: {str(e)}"}


@tool
def ls_directory(path: str = ".", ignore: List[str] = None) -> Dict[str, Any]:
    """List directory contents with filtering - Claude Code equivalent"""
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"Path does not exist: {path}"}
        
        if not os.path.isdir(path):
            return {"success": False, "error": f"Path is not a directory: {path}"}
        
        ignore_patterns = ignore or []
        items = []
        
        for item in os.listdir(path):
            # Check ignore patterns
            if any(fnmatch.fnmatch(item, pattern) for pattern in ignore_patterns):
                continue
            
            item_path = os.path.join(path, item)
            
            try:
                stat = os.stat(item_path)
                is_dir = os.path.isdir(item_path)
                
                items.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "path": item_path,
                    "absolute_path": os.path.abspath(item_path),
                    "size": stat.st_size if not is_dir else None,
                    "modified": stat.st_mtime,
                    "permissions": oct(stat.st_mode)[-3:]
                })
            except:
                # Fallback for items we can't stat
                items.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "path": item_path,
                    "absolute_path": os.path.abspath(item_path)
                })
        
        # Sort: directories first, then files, both alphabetically
        items.sort(key=lambda x: (x['type'] == 'file', x['name'].lower()))
        
        return {
            "success": True,
            "path": path,  
            "absolute_path": os.path.abspath(path),
            "items": items,
            "total": len(items),
            "directories": len([i for i in items if i['type'] == 'directory']),
            "files": len([i for i in items if i['type'] == 'file']),
            "ignored_patterns": ignore_patterns
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied accessing: {path}"}
    except Exception as e:
        return {"success": False, "error": f"Error listing directory: {str(e)}"}


@tool
def grep_search(pattern: str, file_path: str = None, path: str = ".", 
                file_glob: str = "*", context_lines: int = 0, 
                case_insensitive: bool = False) -> Dict[str, Any]:
    """Search within files using regex - Claude Code equivalent"""
    try:
        flags = re.IGNORECASE if case_insensitive else 0
        
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error as e:
            return {"success": False, "error": f"Invalid regex pattern: {e}"}
        
        matches = []
        files_searched = 0
        
        # Determine files to search
        if file_path:
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            files_to_search = [file_path]
        else:
            # Use glob to find files
            if path == ".":
                search_pattern = os.path.join("**", file_glob)
            else:
                search_pattern = os.path.join(path, "**", file_glob)
            
            files_to_search = glob.glob(search_pattern, recursive=True)
            files_to_search = [f for f in files_to_search if os.path.isfile(f)]
        
        for file in files_to_search:
            try:
                files_searched += 1
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    match = compiled_pattern.search(line)
                    if match:
                        match_info = {
                            "file": file,
                            "line_number": line_num,
                            "line": line.rstrip(),
                            "match": match.group(),
                            "match_start": match.start(),
                            "match_end": match.end()
                        }
                        
                        # Add context lines if requested
                        if context_lines > 0:
                            start_line = max(0, line_num - context_lines - 1)
                            end_line = min(len(lines), line_num + context_lines)
                            
                            match_info["context"] = {
                                "before": [lines[i].rstrip() for i in range(start_line, line_num - 1)],
                                "after": [lines[i].rstrip() for i in range(line_num, end_line)]
                            }
                        
                        matches.append(match_info)
                        
            except Exception:
                continue  # Skip files that can't be read
        
        # Group matches by file for summary
        files_with_matches = {}
        for match in matches:
            file = match['file']
            if file not in files_with_matches:
                files_with_matches[file] = []
            files_with_matches[file].append(match['line_number'])
        
        return {
            "success": True,
            "pattern": pattern,
            "case_insensitive": case_insensitive,
            "files_searched": files_searched,
            "files_with_matches": len(files_with_matches),
            "total_matches": len(matches),
            "matches": matches,
            "files_summary": {file: len(lines) for file, lines in files_with_matches.items()},
            "context_lines": context_lines
        }
    except Exception as e:
        return {"success": False, "error": f"Error searching: {str(e)}"}


@tool
def bash_command(command: str, working_dir: str = ".", timeout: int = 60) -> Dict[str, Any]:
    """Execute bash commands - Claude Code equivalent"""
    try:
        if not os.path.exists(working_dir):
            return {"success": False, "error": f"Working directory does not exist: {working_dir}"}
        
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=working_dir,
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "working_dir": os.path.abspath(working_dir),
            "timeout": timeout
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, 
            "error": f"Command timed out after {timeout} seconds",
            "command": command,
            "timeout": timeout
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "Shell not found or command not executable",
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Command execution failed: {str(e)}",
            "command": command
        }


# Export all tools
__all__ = [
    'read_file', 'write_file', 'edit_file', 'multi_edit',
    'glob_files', 'ls_directory', 'grep_search', 'bash_command'
]