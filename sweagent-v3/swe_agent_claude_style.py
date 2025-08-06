"""
SWE Agent Claude Code Style - True Visual Equivalent
Based on ultimate_fixed but with exact Claude Code tool naming and display format
"""

import os
import json
import pickle
import glob
import re
import datetime
import requests
import subprocess
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from anthropic import Anthropic


class ClaudeDisplay:
    """Exact Claude Code display formatting"""
    
    def show_header(self, working_dir: str, tools_count: int):
        """Clean header like Claude Code"""
        print(f"\nClaude Code Agent")
        print(f"Working directory: {working_dir}")
        print(f"Tools available: {tools_count}\n")
    
    def show_task_start(self, task: str):
        """Simple task display"""
        print(f"Task: {task}\n")
    
    def show_tool_start(self, tool_name: str, params: str = ""):
        """Show tool usage exactly like Claude Code"""
        display_name = self._get_tool_display_name(tool_name, params)
        print(f"⏺ {display_name}")
    
    def show_tool_result(self, tool_name: str, params: str, result: Dict[str, Any]):
        """Show tool result in Claude Code format"""
        if result["success"]:
            result_text = self._format_tool_result(tool_name, params, result)
            print(f"  ⎿ {result_text}")
        else:
            error_msg = result.get("error", "Operation failed")
            print(f"  ⎿ Error: {error_msg}")
    
    def _get_tool_display_name(self, tool_name: str, params: str) -> str:
        """Get Claude Code style tool display name"""
        if tool_name == "read_file":
            return f"Read({params})"
        elif tool_name == "edit_file":
            return f"Edit({params})"
        elif tool_name == "bash":
            return f"Bash({params})"
        elif tool_name == "search":
            return f"Search({params})"
        elif tool_name == "glob":
            return f"Glob({params})"
        elif tool_name == "ls":
            return f"LS({params})"
        elif tool_name == "web_search":
            return f"WebSearch({params})"
        else:
            return f"{tool_name.title()}({params})"
    
    def _format_tool_result(self, tool_name: str, params: str, result: Dict[str, Any]) -> str:
        """Format tool results exactly like Claude Code"""
        if tool_name == "read_file":
            lines = result.get("line_count", 0)
            if lines == 0:
                return "File is empty"
            elif lines == 1:
                return "Read 1 line"
            else:
                return f"Read {lines} lines"
                
        elif tool_name == "edit_file":
            operation = result.get("operation", "edit")
            if operation == "create":
                return f"Created {params}"
            elif operation == "replace":
                changes = result.get("changes", 1)
                return f"Made {changes} replacement{'s' if changes != 1 else ''}"
            else:
                return f"Modified {params}"
                
        elif tool_name == "bash":
            returncode = result.get("returncode", 0)
            if returncode == 0:
                output_lines = len(result.get("output", "").split('\n'))
                if output_lines <= 1:
                    return "Command executed successfully"
                else:
                    return f"Command executed ({output_lines} lines output)"
            else:
                return f"Command failed (exit code {returncode})"
                
        elif tool_name == "search":
            matches = result.get("match_count", 0)
            files = result.get("file_count", 0)
            if matches == 0:
                return "No matches found"
            elif matches == 1:
                return f"Found 1 match in {files} file{'s' if files != 1 else ''}"
            else:
                return f"Found {matches} matches in {files} file{'s' if files != 1 else ''}"
                
        elif tool_name == "glob":
            count = result.get("file_count", 0)
            if count == 0:
                return "No files found"
            elif count == 1:
                return "Found 1 file"
            else:
                return f"Found {count} files"
                
        elif tool_name == "ls":
            items = result.get("item_count", 0)
            if items == 0:
                return "Directory is empty"
            elif items == 1:
                return "Listed 1 item"
            else:
                return f"Listed {items} items"
                
        elif tool_name == "web_search":
            results = result.get("result_count", 0)
            if results == 0:
                return "No search results"
            else:
                return f"Found {results} search results"
        
        else:
            return result.get("output", "Operation completed")[:50]
    
    def show_completion_prompt(self, final_response: str, stats: Dict):
        """Claude Code style completion prompt"""
        print(f"\n{final_response}")
        
        # Show clean statistics
        print(f"\nTask Summary:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print(f"\nIs this task complete?")
        print("y - Yes, task is complete")
        print("n - No, continue working") 
        print("c - Continue without feedback")


@dataclass
class Config:
    """Claude Code style configuration"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 50
    debug_mode: bool = False
    state_file: str = ".claude_agent_state.pkl"
    enable_web: bool = True


class ClaudeAgentState:
    """Simplified state for Claude Code style agent"""
    def __init__(self, task_id: str, original_task: str):
        self.task_id = task_id
        self.original_task = original_task
        self.iteration_count = 0
        self.files_created = []
        self.files_modified = []
        self.commands_run = []
        self.searches_performed = []
        self.start_time = datetime.datetime.now()


class ClaudeCodeStyleAgent:
    """Agent matching Claude Code's exact visual style and tool naming"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = self._create_claude_tools()
        self.display = ClaudeDisplay()
        self.state = None
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
        
        self.display.show_header(os.getcwd(), len(self.tools))
    
    def _create_claude_tools(self):
        """Create tools with Claude Code naming conventions"""
        return [
            {
                "name": "read_file",
                "description": "Read file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"},
                        "line_range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "[start_line, end_line] for partial reading"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "edit_file",
                "description": "Edit file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"},
                        "operation": {
                            "type": "string", 
                            "enum": ["create", "replace", "append"],
                            "description": "Type of edit operation"
                        },
                        "content": {"type": "string", "description": "Content for create/append"},
                        "old_text": {"type": "string", "description": "Text to replace"},
                        "new_text": {"type": "string", "description": "Replacement text"}
                    },
                    "required": ["file_path", "operation"]
                }
            },
            {
                "name": "bash",
                "description": "Execute bash commands",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"},
                        "timeout": {"type": "number", "default": 30}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "search",
                "description": "Search for patterns in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Search pattern/regex"},
                        "path": {"type": "string", "default": ".", "description": "Search path"},
                        "file_pattern": {"type": "string", "default": "*", "description": "File pattern filter"},
                        "case_sensitive": {"type": "boolean", "default": True}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "glob",
                "description": "Find files by pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "File pattern (e.g., **/*.py)"},
                        "path": {"type": "string", "default": ".", "description": "Base path"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "ls",
                "description": "List directory contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": ".", "description": "Directory path"},
                        "show_hidden": {"type": "boolean", "default": False}
                    }
                }
            }
        ]
        
        # Add web search if enabled
        if self.config.enable_web:
            self.tools.append({
                "name": "web_search",
                "description": "Search the web",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "number", "default": 5}
                    },
                    "required": ["query"]
                }
            })
    
    def execute_task(self, task: str, resume_task_id: str = None) -> Dict[str, Any]:
        """Execute task with Claude Code style interaction"""
        
        if resume_task_id:
            return self._resume_task(resume_task_id)
        
        # Initialize new task
        task_id = f"claude_task_{int(time.time())}"
        self.state = ClaudeAgentState(task_id, task)
        
        self.display.show_task_start(task)
        
        # Claude Code style system prompt
        system_prompt = f"""You are Claude Code, Anthropic's official software engineering assistant.

You have these tools available:
- read_file: Read file contents  
- edit_file: Create and edit files
- bash: Execute shell commands
- search: Search patterns in files
- glob: Find files by pattern
- ls: List directories
{"- web_search: Search the web" if self.config.enable_web else ""}

Work systematically through the task. Be concise and clear in your communications.

Working directory: {os.getcwd()}
Task: {task}"""

        messages = [{"role": "user", "content": system_prompt}]
        return self._execute_conversation(messages)
    
    def _execute_conversation(self, messages: List[Dict]) -> Dict[str, Any]:
        """Main conversation loop with Claude Code style"""
        
        iteration = 0
        max_iterations = self.config.max_iterations
        
        while iteration < max_iterations:
            try:
                self.state.iteration_count = iteration
                
                # Get Claude's response
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages,
                    tools=self.tools
                )
                
                # Add assistant response
                messages.append({"role": "assistant", "content": response.content})
                
                # Handle tool usage
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id
                            
                            # Show tool start in Claude Code format
                            params = self._format_tool_params(tool_name, tool_input)
                            self.display.show_tool_start(tool_name, params)
                            
                            # Execute tool
                            result = self._execute_claude_tool(tool_name, tool_input)
                            
                            # Show result in Claude Code format
                            self.display.show_tool_result(tool_name, params, result)
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result["output"] if result["success"] else f"Error: {result.get('error', 'Unknown error')}"
                            })
                    
                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                
                else:
                    # Task phase completed
                    final_response = (
                        response.content[0].text if response.content else "Task completed"
                    )
                    return self._handle_completion(final_response, messages, iteration + 1)
                
                iteration += 1
                
            except KeyboardInterrupt:
                print(f"\nTask interrupted")
                return self._save_and_exit(messages, iteration)
                
            except Exception as e:
                print(f"Error: {e}")
                if self.config.debug_mode:
                    import traceback
                    traceback.print_exc()
                
                # Simple error handling
                user_choice = input("Continue? (y/n): ").strip().lower()
                if user_choice != 'y':
                    return self._save_and_exit(messages, iteration)
                
                iteration += 1
        
        print(f"Maximum iterations reached")
        return self._handle_completion("Maximum iterations reached", messages, max_iterations)
    
    def _format_tool_params(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Format tool parameters for display"""
        if tool_name == "read_file":
            path = tool_input["file_path"]
            line_range = tool_input.get("line_range")
            if line_range:
                return f"{path}:{line_range[0]}-{line_range[1]}"
            return path
            
        elif tool_name == "edit_file":
            return tool_input["file_path"]
            
        elif tool_name == "bash":
            cmd = tool_input["command"]
            return cmd[:50] + "..." if len(cmd) > 50 else cmd
            
        elif tool_name == "search":
            pattern = tool_input["pattern"]
            path = tool_input.get("path", ".")
            return f'pattern: "{pattern}", path: "{path}"'
            
        elif tool_name == "glob":
            pattern = tool_input["pattern"]
            return f'"{pattern}"'
            
        elif tool_name == "ls":
            path = tool_input.get("path", ".")
            return path
            
        elif tool_name == "web_search":
            query = tool_input["query"]
            return f'"{query}"'
        
        return str(tool_input)
    
    def _execute_claude_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools with Claude Code style results"""
        try:
            if tool_name == "read_file":
                file_path = tool_input["file_path"]
                line_range = tool_input.get("line_range")
                
                with open(file_path, "r", encoding="utf-8") as f:
                    if line_range:
                        lines = f.readlines()
                        start, end = line_range
                        content = "".join(lines[start-1:end])
                        line_count = end - start + 1
                    else:
                        content = f.read()
                        line_count = len(content.split('\n'))
                
                return {
                    "success": True,
                    "output": content,
                    "line_count": line_count
                }
            
            elif tool_name == "edit_file":
                file_path = tool_input["file_path"]
                operation = tool_input["operation"]
                
                if operation == "create":
                    content = tool_input.get("content", "")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    self.state.files_created.append(file_path)
                    return {
                        "success": True,
                        "output": f"Created {file_path}",
                        "operation": "create"
                    }
                
                elif operation == "replace":
                    old_text = tool_input["old_text"]
                    new_text = tool_input["new_text"]
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if old_text not in content:
                        return {
                            "success": False,
                            "error": f"Text not found in {file_path}"
                        }
                    
                    new_content = content.replace(old_text, new_text)
                    changes = content.count(old_text)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    
                    if file_path not in self.state.files_modified:
                        self.state.files_modified.append(file_path)
                    
                    return {
                        "success": True,
                        "output": f"Made {changes} replacement{'s' if changes != 1 else ''} in {file_path}",
                        "operation": "replace",
                        "changes": changes
                    }
            
            elif tool_name == "bash":
                command = tool_input["command"]
                timeout = tool_input.get("timeout", 30)
                
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=os.getcwd()
                )
                
                output = result.stdout
                if result.stderr:
                    output += f"\nSTDERR: {result.stderr}"
                
                self.state.commands_run.append(command)
                
                return {
                    "success": result.returncode == 0,
                    "output": output or "(No output)",
                    "returncode": result.returncode
                }
            
            elif tool_name == "search":
                pattern = tool_input["pattern"]
                search_path = tool_input.get("path", ".")
                file_pattern = tool_input.get("file_pattern", "*")
                case_sensitive = tool_input.get("case_sensitive", True)
                
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
                
                matches = []
                files_with_matches = set()
                
                # Find files to search
                if os.path.isfile(search_path):
                    files_to_search = [search_path]
                else:
                    files_to_search = glob.glob(
                        os.path.join(search_path, "**", file_pattern), 
                        recursive=True
                    )
                    files_to_search = [f for f in files_to_search if os.path.isfile(f)]
                
                for file_path in files_to_search:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            if regex.search(line):
                                matches.append(f"{file_path}:{i+1}: {line.strip()}")
                                files_with_matches.add(file_path)
                    except:
                        continue
                
                result_text = "\n".join(matches[:20])
                if len(matches) > 20:
                    result_text += f"\n... and {len(matches) - 20} more matches"
                
                self.state.searches_performed.append(pattern)
                
                return {
                    "success": True,
                    "output": result_text,
                    "match_count": len(matches),
                    "file_count": len(files_with_matches)
                }
            
            elif tool_name == "glob":
                pattern = tool_input["pattern"]
                base_path = tool_input.get("path", ".")
                
                if "**" not in pattern:
                    pattern = f"**/{pattern}"
                
                search_pattern = os.path.join(base_path, pattern)
                files = glob.glob(search_pattern, recursive=True)
                files = [f for f in files if os.path.isfile(f)]
                files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                result_text = "\n".join(files[:20])
                if len(files) > 20:
                    result_text += f"\n... and {len(files) - 20} more files"
                
                return {
                    "success": True,
                    "output": result_text,
                    "file_count": len(files)
                }
            
            elif tool_name == "ls":
                path = tool_input.get("path", ".")
                show_hidden = tool_input.get("show_hidden", False)
                
                items = os.listdir(path)
                if not show_hidden:
                    items = [item for item in items if not item.startswith(".")]
                
                formatted_items = []
                for item in sorted(items):
                    full_path = os.path.join(path, item)
                    is_dir = os.path.isdir(full_path)
                    formatted_items.append(f"{'/' if is_dir else ''}{item}")
                
                return {
                    "success": True,
                    "output": "\n".join(formatted_items),
                    "item_count": len(items)
                }
            
            elif tool_name == "web_search":
                query = tool_input["query"]
                num_results = tool_input.get("num_results", 5)
                
                # DuckDuckGo search implementation
                try:
                    search_url = "https://api.duckduckgo.com/"
                    params = {
                        'q': query,
                        'format': 'json',
                        'no_redirect': '1'
                    }
                    
                    headers = {
                        'User-Agent': 'Claude Code Agent 1.0'
                    }
                    
                    response = requests.get(search_url, params=params, headers=headers, timeout=10)
                    data = response.json()
                    
                    # Parse results
                    results = []
                    if 'RelatedTopics' in data:
                        for topic in data['RelatedTopics'][:num_results]:
                            if 'Text' in topic:
                                results.append(topic['Text'])
                    
                    result_text = "\n".join(f"{i+1}. {result}" for i, result in enumerate(results))
                    if not result_text:
                        result_text = f"Search completed for '{query}' but no detailed results available"
                    
                    return {
                        "success": True,
                        "output": result_text,
                        "result_count": len(results)
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Web search failed: {str(e)}"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _handle_completion(self, final_response: str, messages: List[Dict], iterations: int) -> Dict[str, Any]:
        """Handle task completion with Claude Code style prompt"""
        
        stats = {
            "Iterations": iterations,
            "Files created": len(self.state.files_created),
            "Files modified": len(self.state.files_modified),
            "Commands run": len(self.state.commands_run),
            "Searches performed": len(self.state.searches_performed),
            "Duration": str(datetime.datetime.now() - self.state.start_time).split('.')[0]
        }
        
        self.display.show_completion_prompt(final_response, stats)
        
        while True:
            try:
                user_input = input("Your choice: ").strip().lower()
                
                if user_input == "y":
                    print(f"\nTask completed successfully!")
                    self._cleanup_state()
                    return {
                        "success": True,
                        "iterations": iterations,
                        "final_response": final_response,
                        "task_id": self.state.task_id,
                        **stats
                    }
                
                elif user_input == "n":
                    feedback = input("What needs to be done? ").strip()
                    if feedback:
                        messages.append({
                            "role": "user",
                            "content": f"User feedback: {feedback}. Please continue working."
                        })
                        print(f"\nContinuing with feedback...")
                        return self._execute_conversation(messages)
                    else:
                        print("Please provide feedback.")
                        continue
                
                elif user_input == "c":
                    messages.append({
                        "role": "user",
                        "content": "Please continue working on the task."
                    })
                    print(f"\nContinuing task...")
                    return self._execute_conversation(messages)
                
                else:
                    print("Please enter y, n, or c.")
                    continue
                    
            except (KeyboardInterrupt, EOFError):
                return self._save_and_exit(messages, iterations)
    
    def _save_and_exit(self, messages: List[Dict], iterations: int) -> Dict[str, Any]:
        """Save state and exit"""
        try:
            with open(self.config.state_file, 'wb') as f:
                pickle.dump({
                    'state': self.state,
                    'messages': messages,
                    'iterations': iterations
                }, f)
            print(f"\nState saved. Resume with: --resume {self.state.task_id}")
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
        
        return {
            "success": False,
            "iterations": iterations,
            "interrupted": True,
            "task_id": self.state.task_id
        }
    
    def _cleanup_state(self):
        """Clean up state files"""
        try:
            if os.path.exists(self.config.state_file):
                os.remove(self.config.state_file)
        except:
            pass
    
    def _resume_task(self, task_id: str) -> Dict[str, Any]:
        """Resume previous task"""
        try:
            with open(self.config.state_file, 'rb') as f:
                saved_data = pickle.load(f)
            
            self.state = saved_data['state']
            if self.state.task_id != task_id:
                return {"success": False, "error": f"Task ID mismatch"}
            
            messages = saved_data['messages']
            print(f"Resuming task: {self.state.task_id}")
            print(f"Original task: {self.state.original_task}")
            
            return self._execute_conversation(messages)
            
        except FileNotFoundError:
            return {"success": False, "error": f"No saved state found for task {task_id}"}
        except Exception as e:
            return {"success": False, "error": f"Could not resume task: {e}"}


def main():
    """Claude Code style CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Code Style SWE Agent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=50, help="Max iterations")
    parser.add_argument("--resume", help="Resume task by ID")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--no-web", action="store_true", help="Disable web search")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Get task
    if args.resume:
        task = ""
    elif args.task:
        task = " ".join(args.task)
    else:
        task = input("Task: ").strip()
    
    if not task and not args.resume:
        print("Error: No task provided")
        return
    
    # Create config
    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug,
        enable_web=not args.no_web
    )
    
    try:
        agent = ClaudeCodeStyleAgent(config)
        result = agent.execute_task(task, resume_task_id=args.resume)
        
        if not result["success"]:
            if result.get("interrupted"):
                print("Task was interrupted")
            else:
                print("Task failed")
                
    except Exception as e:
        print(f"Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()