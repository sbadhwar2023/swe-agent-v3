"""
SWE Agent V3 Enhanced - True Claude Code Equivalent
Full feature set: advanced file ops, search, task management, sub-agents, web access
"""

import os
import json
import glob
import re
import subprocess
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from anthropic import Anthropic


@dataclass
class Config:
    """Enhanced agent configuration"""

    api_key: str
    working_dir: str = "."
    max_iterations: int = 20
    debug_mode: bool = False
    enable_web: bool = True


def create_enhanced_tool_schema():
    """Create comprehensive tool schema matching Claude Code"""
    return [
        # Core execution
        {
            "name": "bash",
            "description": "Execute bash commands and scripts",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
        # Basic file operations (enhanced)
        {
            "name": "str_replace_editor",
            "description": "Create, read, and edit files with advanced options",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "view", "view_range"],
                        "description": "The command to execute",
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {
                        "type": "string",
                        "description": "Content for create command",
                    },
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                    "view_range": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "[start_line, end_line]",
                    },
                },
                "required": ["command", "path"],
            },
        },
        # Advanced file operations
        {
            "name": "glob_search",
            "description": "Find files using patterns (like **/*.py, src/**/*.js)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base path to search in",
                        "default": ".",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively",
                        "default": True,
                    },
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "list_directory",
            "description": "List directory contents with detailed information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path",
                        "default": ".",
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files",
                        "default": False,
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List recursively",
                        "default": False,
                    },
                },
            },
        },
        # Search tools
        {
            "name": "grep_search",
            "description": "Search for patterns within files using regex",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search in",
                        "default": ".",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to limit search",
                        "default": "*",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search",
                        "default": True,
                    },
                    "context_lines": {
                        "type": "number",
                        "description": "Lines of context around matches",
                        "default": 0,
                    },
                },
                "required": ["pattern"],
            },
        },
        # Task management
        {
            "name": "todo_write",
            "description": "Create and manage task lists with progress tracking",
            "input_schema": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                            },
                            "required": ["id", "content", "status", "priority"],
                        },
                    }
                },
                "required": ["todos"],
            },
        },
        # Sub-agent spawning
        {
            "name": "task_agent",
            "description": "Launch specialized sub-agents for complex analysis or tasks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Brief description of the task",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Detailed prompt for the sub-agent",
                    },
                    "agent_type": {
                        "type": "string",
                        "enum": [
                            "search",
                            "analysis",
                            "coding",
                            "debugging",
                            "general",
                        ],
                        "description": "Type of specialized agent",
                        "default": "general",
                    },
                },
                "required": ["description", "prompt"],
            },
        },
        # Web access (if enabled)
        {
            "name": "web_fetch",
            "description": "Fetch and analyze web content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "prompt": {
                        "type": "string",
                        "description": "What to analyze in the content",
                    },
                },
                "required": ["url", "prompt"],
            },
        },
        {
            "name": "web_search",
            "description": "Search the web for information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "number",
                        "description": "Number of results",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
        # Jupyter notebook support
        {
            "name": "notebook_edit",
            "description": "Create, read, and edit Jupyter notebooks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "read", "add_cell", "edit_cell", "run_cell"],
                        "description": "Notebook operation",
                    },
                    "path": {"type": "string", "description": "Notebook path"},
                    "cell_content": {
                        "type": "string",
                        "description": "Cell content for add/edit",
                    },
                    "cell_type": {
                        "type": "string",
                        "enum": ["code", "markdown"],
                        "default": "code",
                    },
                    "cell_index": {
                        "type": "number",
                        "description": "Cell index for edit operations",
                    },
                },
                "required": ["command", "path"],
            },
        },
    ]


class TodoManager:
    """Enhanced todo management with rich display"""

    def __init__(self):
        self.todos = {}

    def update_todos(self, todos_data: List[Dict]) -> str:
        """Update todos and return formatted display"""
        for todo in todos_data:
            self.todos[todo["id"]] = todo

        # Display like Claude Code
        output = "⏺ Update Todos\n"
        for todo in todos_data:
            status_symbol = {"pending": "☐", "in_progress": "🔄", "completed": "☒"}
            symbol = status_symbol.get(todo["status"], "☐")
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            priority = priority_emoji.get(todo["priority"], "")
            output += f"  ⎿  {symbol} {todo['content']} {priority}\n"

        return output


class EnhancedSWEAgent:
    """Full-featured SWE agent equivalent to Claude Code"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_enhanced_tool_schema()
        self.todo_manager = TodoManager()

        # Filter tools based on config
        if not config.enable_web:
            self.tools = [
                t for t in self.tools if t["name"] not in ["web_fetch", "web_search"]
            ]

        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)

        print(f"🚀 Enhanced SWE Agent V3 - Full Claude Code Equivalent")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"🔧 Tools available: {len(self.tools)} tools")
        print(f"   📄 File: str_replace_editor, glob_search, list_directory")
        print(f"   🔍 Search: grep_search")
        print(f"   ⚡ Execute: bash")
        print(f"   📝 Management: todo_write, task_agent")
        if config.enable_web:
            print(f"   🌐 Web: web_fetch, web_search")
        print(f"   📓 Notebooks: notebook_edit")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute complex software engineering tasks with full tool suite"""

        print(f"\n📋 Task: {task}")

        # Enhanced system prompt for intelligent task decomposition
        system_prompt = f"""You are an advanced software engineering assistant with the full Claude Code tool suite.

You have access to these powerful tools:

📄 FILE OPERATIONS:
- str_replace_editor: Create, read, edit files (with view_range for large files)
- glob_search: Find files using patterns like **/*.py, src/**/*.js
- list_directory: Rich directory listings with metadata

🔍 SEARCH & ANALYSIS:
- grep_search: Regex search across files with context
- task_agent: Spawn specialized sub-agents for complex analysis

⚡ EXECUTION:
- bash: Run any shell commands, git operations, build tools

📝 PROJECT MANAGEMENT:
- todo_write: Create interactive task lists with progress tracking

🌐 WEB ACCESS: {"web_fetch, web_search for online resources" if self.config.enable_web else "Disabled"}

📓 NOTEBOOKS:
- notebook_edit: Full Jupyter notebook support

INTELLIGENT BEHAVIOR:
1. **Break down complex tasks** - Use todo_write to plan multi-step work
2. **Use appropriate tools** - glob_search for finding files, grep_search for code analysis
3. **Spawn sub-agents** - Use task_agent for complex analysis or specialized work
4. **Be systematic** - Show progress, verify results, handle errors gracefully
5. **Understand context** - Analyze project structure, dependencies, patterns

Working directory: {os.getcwd()}

Execute this task completely and intelligently, using the full power of your tool suite."""

        messages = [{"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}]

        iteration = 0
        max_iterations = self.config.max_iterations

        while iteration < max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {iteration + 1}")

                # Get response with enhanced tools
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages,
                    tools=self.tools,
                )

                # Add assistant response to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools if used
                if response.stop_reason == "tool_use":
                    tool_results = []

                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            print(f"🔧 Using {tool_name}")

                            # Execute enhanced tool
                            result = self._execute_enhanced_tool(tool_name, tool_input)

                            # Rich display of results
                            self._display_tool_result(tool_name, tool_input, result)

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result["output"]
                                    if result["success"]
                                    else f"Error: {result.get('error', 'Unknown error')}",
                                }
                            )

                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})

                else:
                    # Task completed
                    final_response = (
                        response.content[0].text
                        if response.content
                        else "Task completed"
                    )
                    print("✅ Task completed successfully!")

                    return {
                        "success": True,
                        "iterations": iteration + 1,
                        "final_response": final_response,
                        "messages": messages,
                    }

                iteration += 1

            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")
                if self.config.debug_mode:
                    import traceback

                    traceback.print_exc()

                return {
                    "success": False,
                    "iterations": iteration + 1,
                    "error": str(e),
                    "messages": messages,
                }

        print("⚠️ Max iterations reached")
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max iterations reached",
            "messages": messages,
        }

    def _execute_enhanced_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute enhanced tools with full Claude Code functionality"""

        try:
            if tool_name == "bash":
                return self._execute_bash(
                    tool_input["command"], tool_input.get("timeout", 30)
                )

            elif tool_name == "str_replace_editor":
                return self._execute_str_replace_editor(tool_input)

            elif tool_name == "glob_search":
                return self._execute_glob_search(tool_input)

            elif tool_name == "list_directory":
                return self._execute_list_directory(tool_input)

            elif tool_name == "grep_search":
                return self._execute_grep_search(tool_input)

            elif tool_name == "todo_write":
                return self._execute_todo_write(tool_input)

            elif tool_name == "task_agent":
                return self._execute_task_agent(tool_input)

            elif tool_name == "web_fetch":
                return self._execute_web_fetch(tool_input)

            elif tool_name == "web_search":
                return self._execute_web_search(tool_input)

            elif tool_name == "notebook_edit":
                return self._execute_notebook_edit(tool_input)

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_bash(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Enhanced bash execution with better error handling"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output or "(No output)",
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_str_replace_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced file operations with range viewing"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(tool_input.get("file_text", ""))
                return {"success": True, "output": f"Created file: {path}"}

            elif command == "view":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {"success": True, "output": content}

            elif command == "view_range":
                start_line, end_line = tool_input["view_range"]
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                content = "".join(lines[start_line - 1 : end_line])
                return {"success": True, "output": content}

            elif command == "str_replace":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]

                if old_str not in content:
                    return {
                        "success": False,
                        "error": f"String not found: {old_str[:50]}...",
                    }

                new_content = content.replace(old_str, new_str)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {"success": True, "output": f"Replaced text in {path}"}

            else:
                return {
                    "success": False,
                    "error": f"Unknown str_replace_editor command: {command}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_glob_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Find files using glob patterns"""
        try:
            pattern = tool_input["pattern"]
            base_path = tool_input.get("path", ".")
            recursive = tool_input.get("recursive", True)

            if recursive and "**" not in pattern:
                pattern = f"**/{pattern}"

            search_pattern = os.path.join(base_path, pattern)
            files = glob.glob(search_pattern, recursive=recursive)

            # Filter to only files, sort by modification time
            files = [f for f in files if os.path.isfile(f)]
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            return {
                "success": True,
                "output": f"Found {len(files)} files:\n"
                + "\n".join(files[:20])
                + (f"\n... and {len(files)-20} more" if len(files) > 20 else ""),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_list_directory(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced directory listing"""
        try:
            path = tool_input.get("path", ".")
            show_hidden = tool_input.get("show_hidden", False)
            recursive = tool_input.get("recursive", False)

            if recursive:
                items = []
                for root, dirs, files in os.walk(path):
                    if not show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        files = [f for f in files if not f.startswith(".")]

                    for name in dirs + files:
                        full_path = os.path.join(root, name)
                        rel_path = os.path.relpath(full_path, path)
                        is_dir = os.path.isdir(full_path)
                        items.append(f"{'📁' if is_dir else '📄'} {rel_path}")

                return {"success": True, "output": "\n".join(sorted(items))}

            else:
                items = os.listdir(path)
                if not show_hidden:
                    items = [item for item in items if not item.startswith(".")]

                formatted_items = []
                for item in sorted(items):
                    full_path = os.path.join(path, item)
                    is_dir = os.path.isdir(full_path)
                    size = "" if is_dir else f" ({os.path.getsize(full_path)} bytes)"
                    formatted_items.append(f"{'📁' if is_dir else '📄'} {item}{size}")

                return {"success": True, "output": "\n".join(formatted_items)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_grep_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Search within files using regex"""
        try:
            pattern = tool_input["pattern"]
            search_path = tool_input.get("path", ".")
            file_pattern = tool_input.get("file_pattern", "*")
            case_sensitive = tool_input.get("case_sensitive", True)
            context_lines = tool_input.get("context_lines", 0)

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            matches = []

            # Find files to search
            if os.path.isfile(search_path):
                files_to_search = [search_path]
            else:
                files_to_search = glob.glob(
                    os.path.join(search_path, "**", file_pattern), recursive=True
                )
                files_to_search = [f for f in files_to_search if os.path.isfile(f)]

            for file_path in files_to_search:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            match_info = f"{file_path}:{i+1}: {line.strip()}"
                            matches.append(match_info)

                            # Add context if requested
                            if context_lines > 0:
                                start = max(0, i - context_lines)
                                end = min(len(lines), i + context_lines + 1)
                                for j in range(start, end):
                                    if j != i:
                                        matches.append(
                                            f"{file_path}:{j+1}: {lines[j].strip()}"
                                        )
                                matches.append("---")

                except Exception:
                    continue

            return {
                "success": True,
                "output": f"Found {len([m for m in matches if ':' in m and not m.startswith('---')])} matches:\n"
                + "\n".join(matches[:50])
                + (f"\n... and more" if len(matches) > 50 else ""),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_todo_write(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Rich todo management with visual feedback"""
        try:
            todos_data = tool_input["todos"]
            output = self.todo_manager.update_todos(todos_data)

            return {"success": True, "output": output}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_task_agent(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn specialized sub-agents"""
        try:
            description = tool_input["description"]
            prompt = tool_input["prompt"]
            agent_type = tool_input.get("agent_type", "general")

            print(f"🤖 Spawning {agent_type} sub-agent: {description}")

            # Create sub-agent with limited iterations
            sub_config = Config(
                api_key=self.config.api_key,
                working_dir=self.config.working_dir,
                max_iterations=5,  # Limit sub-agent iterations
                debug_mode=False,
                enable_web=False,  # Disable web for sub-agents
            )

            # Create specialized tools for sub-agent based on type
            if agent_type == "search":
                sub_tools = [
                    t
                    for t in self.tools
                    if t["name"] in ["glob_search", "grep_search", "str_replace_editor"]
                ]
            elif agent_type == "analysis":
                sub_tools = [
                    t
                    for t in self.tools
                    if t["name"] in ["str_replace_editor", "grep_search", "bash"]
                ]
            else:
                sub_tools = self.tools[:4]  # Basic tool set

            sub_agent = EnhancedSWEAgent.__new__(EnhancedSWEAgent)
            sub_agent.config = sub_config
            sub_agent.client = self.client
            sub_agent.tools = sub_tools
            sub_agent.todo_manager = TodoManager()

            result = sub_agent.execute_task(prompt)

            return {
                "success": result["success"],
                "output": f"Sub-agent ({agent_type}) completed in {result['iterations']} iterations:\n{result['final_response']}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_web_fetch(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and analyze web content"""
        try:
            url = tool_input["url"]
            prompt = tool_input["prompt"]

            # Simple web fetch (in real implementation, would use proper web scraping)
            response = requests.get(url, timeout=10)
            content = response.text[:5000]  # Limit content

            return {
                "success": True,
                "output": f"Fetched content from {url}:\n{content}...\n\nAnalysis prompt: {prompt}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_web_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web (placeholder implementation)"""
        try:
            query = tool_input["query"]
            num_results = tool_input.get("num_results", 5)

            # Placeholder - in real implementation would use search API
            return {
                "success": True,
                "output": f"Web search for '{query}' (placeholder - would return {num_results} results)",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_notebook_edit(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Jupyter notebook operations"""
        try:
            command = tool_input["command"]
            path = tool_input["path"]

            if command == "create":
                notebook = {
                    "cells": [],
                    "metadata": {},
                    "nbformat": 4,
                    "nbformat_minor": 4,
                }
                with open(path, "w") as f:
                    json.dump(notebook, f, indent=2)
                return {"success": True, "output": f"Created notebook: {path}"}

            elif command == "read":
                with open(path, "r") as f:
                    notebook = json.load(f)
                return {
                    "success": True,
                    "output": f"Notebook has {len(notebook['cells'])} cells",
                }

            # Other notebook operations would be implemented here
            else:
                return {
                    "success": False,
                    "error": f"Notebook command '{command}' not implemented",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _display_tool_result(self, tool_name: str, tool_input: Dict, result: Dict):
        """Rich display of tool results like Claude Code"""
        if result["success"]:
            if tool_name == "todo_write":
                # TodoWrite displays itself
                print(result["output"])
            elif tool_name == "bash":
                print(f"  ✅ Command executed")
                if result.get("output") and result["output"] != "(No output)":
                    print(f"  📄 Output: {result['output'][:200]}...")
            elif tool_name in ["glob_search", "grep_search"]:
                lines = result["output"].split("\n")
                print(f"  ✅ Found results")
                print(f"  📄 {lines[0]}")
            elif tool_name == "task_agent":
                print(f"  ✅ Sub-agent completed")
                print(f"  📄 {result['output'][:100]}...")
            else:
                print(f"  ✅ {tool_name} completed")
        else:
            print(f"  ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")


def main():
    """Enhanced CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced SWE Agent V3 - Full Claude Code Equivalent"
    )
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument(
        "--max-iterations", type=int, default=20, help="Maximum iterations"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-web", action="store_true", help="Disable web access")

    args = parser.parse_args()

    # Get task
    if args.task:
        task = " ".join(args.task)
    else:
        task = input("Enter task: ").strip()

    if not task:
        print("❌ No task provided")
        return

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return

    # Create enhanced config and agent
    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug,
        enable_web=not args.no_web,
    )

    try:
        agent = EnhancedSWEAgent(config)
        result = agent.execute_task(task)

        print(f"\n📊 Enhanced Agent Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")

        if not result["success"] and "error" in result:
            print(f"❌ Error: {result['error']}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
