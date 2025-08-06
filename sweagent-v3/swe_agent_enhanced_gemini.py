"""
SWE Agent V4 - Interactive & Collaborative
Full feature set with interactive error handling, user feedback loop, and explicit task completion.
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
    max_iterations: int = 50 # Increased for more complex, interactive tasks
    debug_mode: bool = False
    enable_web: bool = True


def create_interactive_tool_schema():
    """Create a comprehensive tool schema with an interactive feedback loop."""
    base_tools = create_enhanced_tool_schema()
    # Add the crucial tool for explicit task completion
    base_tools.append({
        "name": "finish_task",
        "description": "Call this function ONLY when the task is fully completed, verified, and successful.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "A brief summary of why the task is considered complete."
                }
            },
            "required": ["reason"]
        }
    })
    return base_tools

# NOTE: The original 'create_enhanced_tool_schema' function is assumed to be here.
# For brevity, we will redefine it to show the full context.
def create_enhanced_tool_schema():
    """Create comprehensive tool schema """
    return [
        # Core execution
        {
            "name": "bash",
            "description": "Execute bash commands and scripts. CRITICAL: For long-running commands like starting a server, run them in the background (`&`) and use `sleep` to wait for them to initialize.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                    "timeout": {"type": "number", "description": "Timeout in seconds", "default": 60}
                },
                "required": ["command"]
            }
        },
        # Basic file operations
        {
            "name": "str_replace_editor",
            "description": "Create, read, and edit files. Use for all file manipulations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "view", "view_range"],
                        "description": "The command to execute"
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {"type": "string", "description": "Content for create command"},
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                    "view_range": {"type": "array", "items": {"type": "number"}, "description": "[start_line, end_line]"}
                },
                "required": ["command", "path"]
            }
        },
        # Advanced file operations
        {
            "name": "glob_search",
            "description": "Find files using patterns (like **/*.py, src/**/*.js)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to search for"},
                    "path": {"type": "string", "description": "Base path to search in", "default": "."},
                    "recursive": {"type": "boolean", "description": "Search recursively", "default": True}
                },
                "required": ["pattern"]
            }
        },
        # Search tools
        {
            "name": "grep_search",
            "description": "Search for patterns within files using regex.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "File or directory to search in", "default": "."}
                },
                "required": ["pattern"]
            }
        },
        # Task management
        {
            "name": "todo_write",
            "description": "Create and manage task lists to track progress.",
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
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                            },
                            "required": ["id", "content", "status", "priority"]
                        }
                    }
                },
                "required": ["todos"]
            }
        },
    ]


class TodoManager:
    """Enhanced todo management with rich display"""
    def __init__(self):
        self.todos = {}

    def update_todos(self, todos_data: List[Dict]) -> str:
        """Update todos and return formatted display"""
        for todo in todos_data:
            self.todos[todo['id']] = todo

        output = "⏺  Updated Todos\n"
        for todo_id in sorted(self.todos.keys()):
            todo = self.todos[todo_id]
            status_symbol = {"pending": "☐", "in_progress": "🔄", "completed": "✅"}
            symbol = status_symbol.get(todo['status'], "☐")
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "�"}
            priority = priority_emoji.get(todo['priority'], "")
            output += f"  ⎿  {symbol} {todo['content']} {priority}\n"

        return output


class InteractiveSWEAgent:
    """A collaborative SWE agent with an interactive feedback loop."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_interactive_tool_schema()
        self.todo_manager = TodoManager()

        if config.working_dir != ".":
            os.makedirs(config.working_dir, exist_ok=True)
            os.chdir(config.working_dir)

        print("🚀 Interactive SWE Agent V4 Initialized")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"🔧 Tools available: {[t['name'] for t in self.tools]}")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Executes a task with an interactive loop for error handling."""
        print(f"\n📋 New Task: {task}")

        system_prompt = f"""You are an expert software engineering assistant. Your goal is to solve tasks by breaking them down and using the available tools.

Key Instructions:
1.  **Plan First:** Start by using `todo_write` to create a detailed plan.
2.  **Be Methodical:** Execute your plan step-by-step. Verify each step.
3.  **Handle Errors:** If a tool fails, analyze the error. You can ask the user for help.
4.  **CRITICAL - FINISHING:** Do NOT assume the task is done. You MUST call the `finish_task` tool when you have successfully completed and VERIFIED the entire task. Do not call it otherwise.

Working directory: {os.getcwd()}
Execute this task completely and intelligently."""

        messages = [{"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}]
        iteration = 0

        while iteration < self.config.max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4096,
                    messages=messages,
                    tools=self.tools,
                    tool_choice={"type": "auto"}
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "tool_use":
                    all_tool_results = []
                    has_failure = False

                    for tool_call in response.content:
                        if tool_call.type != "tool_use": continue

                        tool_name = tool_call.name
                        tool_input = tool_call.input
                        tool_use_id = tool_call.id

                        print(f"🤖 Agent wants to use: {tool_name}")
                        if self.config.debug_mode: print(f"   Input: {tool_input}")

                        if tool_name == "finish_task":
                            print(f"✅ Agent signaled task completion: {tool_input.get('reason')}")
                            return {
                                "success": True,
                                "iterations": iteration,
                                "final_response": tool_input.get('reason', 'Task completed.'),
                                "messages": messages
                            }

                        result = self._execute_tool(tool_name, tool_input)

                        if not result["success"]:
                            has_failure = True
                            print(f"❌ TOOL FAILED: {tool_name}")
                            print(f"   Error: {result.get('error', 'Unknown error')}")
                            
                            # INTERACTIVE FEEDBACK LOOP
                            user_feedback = input("   👉 Provide a suggestion to fix this, or press Enter to let the agent decide: ")
                            
                            feedback_content = f"The tool {tool_name} failed with this error: {result.get('error')}. "
                            if user_feedback:
                                feedback_content += f"The user suggests the following: '{user_feedback}'"
                            else:
                                feedback_content += "Please analyze the error and try a different approach."
                            
                            all_tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": feedback_content,
                                "is_error": True,
                            })
                        else:
                            print(f"✅ Tool executed successfully: {tool_name}")
                            if self.config.debug_mode: print(f"   Output: {result['output']}")
                            all_tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result["output"],
                            })

                    # Add all tool results to the conversation history
                    messages.append({"role": "user", "content": all_tool_results})

                else: # Stop reason is 'end_turn'
                    final_text = response.content[0].text if response.content and response.content[0].type == 'text' else "No final message."
                    print(f"⚠️ Agent stopped without finishing. Final message: {final_text}")
                    return {
                        "success": False,
                        "iterations": iteration,
                        "error": "Agent stopped without calling finish_task.",
                        "messages": messages
                    }

            except Exception as e:
                print(f"💥 An unexpected error occurred in the agent loop: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e), "messages": messages}

        print("⚠️ Max iterations reached.")
        return {"success": False, "error": "Max iterations reached", "messages": messages}


    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatcher for tool execution."""
        try:
            if tool_name == "bash":
                return self._execute_bash(tool_input.get("command", ""), tool_input.get("timeout", 60))
            elif tool_name == "str_replace_editor":
                return self._execute_str_replace_editor(tool_input)
            elif tool_name == "glob_search":
                return self._execute_glob_search(tool_input)
            elif tool_name == "grep_search":
                return self._execute_grep_search(tool_input)
            elif tool_name == "todo_write":
                return self._execute_todo_write(tool_input)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"success": False, "error": f"Exception during tool execution: {str(e)}"}

    # --- Tool Implementation Functions ---

    def _execute_bash(self, command: str, timeout: int) -> Dict[str, Any]:
        """Executes a bash command."""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=os.getcwd()
            )
            if result.returncode == 0:
                return {"success": True, "output": result.stdout or "Command executed successfully."}
            else:
                return {"success": False, "error": f"Exit Code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command '{command[:50]}...' timed out after {timeout}s."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_str_replace_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Executes file operations."""
        command = tool_input["command"]
        path = Path(tool_input["path"])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if command == "create":
                path.write_text(tool_input.get("file_text", ""), encoding='utf-8')
                return {"success": True, "output": f"File created at {path}"}
            
            if not path.exists(): return {"success": False, "error": f"File not found: {path}"}

            if command == "view":
                return {"success": True, "output": path.read_text(encoding='utf-8')}
            elif command == "view_range":
                start, end = tool_input["view_range"]
                lines = path.read_text(encoding='utf-8').splitlines()
                return {"success": True, "output": "\n".join(lines[start-1:end])}
            elif command == "str_replace":
                content = path.read_text(encoding='utf-8')
                new_content = content.replace(tool_input["old_str"], tool_input["new_str"])
                if content == new_content:
                    return {"success": False, "error": "String to be replaced was not found in the file."}
                path.write_text(new_content, encoding='utf-8')
                return {"success": True, "output": f"Successfully replaced string in {path}"}
            else:
                return {"success": False, "error": f"Unknown editor command: {command}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_glob_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Finds files using glob patterns."""
        pattern = tool_input["pattern"]
        files = [str(p) for p in Path(".").rglob(pattern)]
        return {"success": True, "output": f"Found files:\n" + "\n".join(files)}

    def _execute_grep_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Searches for a regex pattern in files."""
        pattern = re.compile(tool_input["pattern"])
        search_path = Path(tool_input.get("path", "."))
        matches = []
        files_to_search = list(search_path.rglob("*")) if search_path.is_dir() else [search_path]

        for file in files_to_search:
            if file.is_file():
                try:
                    content = file.read_text(encoding='utf-8', errors='ignore')
                    if pattern.search(content):
                        matches.append(str(file))
                except Exception:
                    continue
        return {"success": True, "output": "Found pattern in files:\n" + "\n".join(matches)}

    def _execute_todo_write(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Updates the todo list."""
        return {"success": True, "output": self.todo_manager.update_todos(tool_input["todos"])}


# --- Example Usage ---
if __name__ == '__main__':
    # IMPORTANT: Replace with your actual Anthropic API key
    # You can get a key from https://www.anthropic.com/
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("🚨 ANTHROPIC_API_KEY environment variable not set!")
        # As a fallback for demonstration, you can uncomment the next line and paste your key.
        # api_key = "YOUR_ANTHROPIC_API_KEY" 
    
    if not api_key:
        exit()

    # Create a unique working directory for this run
    run_dir = "swe_agent_run"
    if os.path.exists(run_dir):
        import shutil
        shutil.rmtree(run_dir)
    os.makedirs(run_dir)

    config = Config(
        api_key=api_key,
        working_dir=run_dir,
        debug_mode=False
    )

    agent = InteractiveSWEAgent(config)

    # The task that previously failed
    # task = "Build a simple Flask web application that shows the weather. It should have one page with a form to enter a city name. When the form is submitted, it should display the current temperature for that city. You will need a free weather API key; sign up for one if necessary and store it securely."
    print("📝 Please enter the task description (end with an empty line):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    task = "\n".join(lines)    


    result = agent.execute_task(task)

    print("\n--- Task Execution Finished ---")
    print(f"Status: {'Success' if result['success'] else 'Failure'}")
    print(f"Total Iterations: {result['iterations']}")
    if result.get('error'):
        print(f"Error: {result['error']}")
