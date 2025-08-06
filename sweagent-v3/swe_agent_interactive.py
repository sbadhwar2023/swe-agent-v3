"""
SWE Agent V3 Interactive - Fixed version with user interaction and error handling
Addresses context issues and adds interactive debugging
"""

import os
import json
import glob
import re
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class Config:
    """Interactive agent configuration"""

    api_key: str
    working_dir: str = "."
    max_iterations: int = 15
    debug_mode: bool = True
    interactive_mode: bool = True
    context_limit: int = 3000  # Prevent context overflow


def create_core_tool_schema():
    """Core tools only - prevent context overflow"""
    return [
        {
            "name": "bash",
            "description": "Execute bash commands with timeout handling",
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
                        "default": 10,
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "file_editor",
            "description": "Create, read, and edit files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "read", "edit", "append"],
                        "description": "File operation to perform",
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {
                        "type": "string",
                        "description": "Content for create/append/edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Text to replace (for edit)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text (for edit)",
                    },
                },
                "required": ["action", "path"],
            },
        },
        {
            "name": "find_files",
            "description": "Find files using simple patterns",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File pattern (*.py, app.*, etc)",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "search_in_files",
            "description": "Search for text within files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to search for"},
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to search in",
                        "default": "*.py",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "ask_user",
            "description": "Ask user for input when encountering issues or needing clarification",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask the user",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about why asking",
                    },
                },
                "required": ["question"],
            },
        },
        {
            "name": "task_agent",
            "description": "Spawn a focused sub-agent for specific tasks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "What the sub-agent should do",
                    },
                    "tools_needed": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which tools the sub-agent needs",
                        "default": ["file_editor", "bash"],
                    },
                },
                "required": ["task_description"],
            },
        },
    ]


class InteractiveSWEAgent:
    """Interactive SWE agent with error handling and user feedback"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_core_tool_schema()
        self.conversation_history = []

        if config.working_dir != ".":
            os.chdir(config.working_dir)

        print(f"🚀 Interactive SWE Agent V3")
        print(f"📁 Working directory: {os.getcwd()}")
        print(
            f"🔧 Core tools: bash, file_editor, find_files, search_in_files, ask_user, task_agent"
        )
        print(f"💬 Interactive mode: {'ON' if config.interactive_mode else 'OFF'}")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with interactive error handling"""

        print(f"\n📋 Task: {task}")

        system_prompt = f"""You are an interactive software engineering assistant. When you encounter errors or issues:

1. **Use ask_user tool** to get user input for clarification or solutions
2. **Be persistent** - don't give up on errors, ask for help or try alternatives
3. **Test your work** - actually run and verify what you create
4. **Use task_agent** for complex sub-tasks that need focused attention

Available tools:
- bash: Execute commands (with shorter timeouts)
- file_editor: Create, read, edit files
- find_files: Find files by pattern
- search_in_files: Search text in files  
- ask_user: Get user input when stuck
- task_agent: Spawn sub-agents for complex tasks

Working directory: {os.getcwd()}

IMPORTANT: If something fails or times out, use ask_user to get guidance before continuing.
Don't declare success until you've actually verified the result works."""

        self.conversation_history = [
            {"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}
        ]

        iteration = 0

        while iteration < self.config.max_iterations:
            try:
                print(f"\n🔍 Iteration {iteration + 1}")

                # Truncate conversation if too long
                messages = self._truncate_conversation()

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=3000,
                    messages=messages,
                    tools=self.tools,
                )

                self.conversation_history.append(
                    {"role": "assistant", "content": response.content}
                )

                if response.stop_reason == "tool_use":
                    tool_results = []

                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            print(f"🔧 Using {tool_name}")

                            # Execute tool with error handling
                            result = self._execute_tool_safely(tool_name, tool_input)

                            # Handle interactive user input
                            if tool_name == "ask_user" and result["success"]:
                                user_response = self._get_user_input(
                                    tool_input["question"],
                                    tool_input.get("context", ""),
                                )
                                result["output"] = user_response

                            self._display_tool_result(tool_name, result)

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result["output"]
                                    if result["success"]
                                    else f"Error: {result.get('error', 'Unknown error')}",
                                }
                            )

                    self.conversation_history.append(
                        {"role": "user", "content": tool_results}
                    )

                else:
                    # Check if actually complete
                    final_response = (
                        response.content[0].text if response.content else ""
                    )

                    if self._is_task_really_complete(final_response):
                        print("✅ Task verified as complete!")
                        return {
                            "success": True,
                            "iterations": iteration + 1,
                            "final_response": final_response,
                        }
                    else:
                        # Ask user if task seems incomplete
                        if self.config.interactive_mode:
                            user_input = (
                                input(
                                    f"\n❓ Agent thinks task is complete. Do you agree? (y/n/continue): "
                                )
                                .strip()
                                .lower()
                            )
                            if user_input == "y":
                                return {
                                    "success": True,
                                    "iterations": iteration + 1,
                                    "final_response": final_response,
                                }
                            elif user_input == "continue":
                                self.conversation_history.append(
                                    {
                                        "role": "user",
                                        "content": "User says task is not complete yet. Please continue working.",
                                    }
                                )
                            else:
                                feedback = input("What still needs to be done? ")
                                self.conversation_history.append(
                                    {
                                        "role": "user",
                                        "content": f"User feedback: {feedback}",
                                    }
                                )
                        else:
                            break

                iteration += 1

            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")

                if self.config.interactive_mode:
                    user_input = (
                        input(f"\nError occurred. Continue anyway? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if user_input != "y":
                        return {
                            "success": False,
                            "iterations": iteration + 1,
                            "error": str(e),
                        }

                    self.conversation_history.append(
                        {
                            "role": "user",
                            "content": f"Error occurred: {e}. User chose to continue. Please try a different approach.",
                        }
                    )
                else:
                    return {
                        "success": False,
                        "iterations": iteration + 1,
                        "error": str(e),
                    }

                iteration += 1

        print("⚠️ Max iterations reached")
        return {
            "success": False,
            "iterations": self.config.max_iterations,
            "error": "Max iterations reached",
        }

    def _execute_tool_safely(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tools with comprehensive error handling"""

        try:
            if tool_name == "bash":
                return self._execute_bash(
                    tool_input["command"], tool_input.get("timeout", 10)
                )

            elif tool_name == "file_editor":
                return self._execute_file_editor(tool_input)

            elif tool_name == "find_files":
                return self._execute_find_files(tool_input)

            elif tool_name == "search_in_files":
                return self._execute_search_in_files(tool_input)

            elif tool_name == "ask_user":
                return {"success": True, "output": "User input requested"}

            elif tool_name == "task_agent":
                return self._execute_task_agent(tool_input)

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    def _execute_bash(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute bash with better timeout handling"""
        try:
            print(f"  🔧 Running: {command}")

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

    def _execute_file_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operations"""
        action = tool_input["action"]
        path = tool_input["path"]

        try:
            if action == "create":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(tool_input.get("content", ""))
                return {"success": True, "output": f"Created {path}"}

            elif action == "read":
                if not os.path.exists(path):
                    return {"success": False, "error": f"File not found: {path}"}
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "success": True,
                    "output": content[:1000] + "..."
                    if len(content) > 1000
                    else content,
                }

            elif action == "edit":
                if not os.path.exists(path):
                    return {"success": False, "error": f"File not found: {path}"}

                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                old_text = tool_input["old_text"]
                new_text = tool_input["new_text"]

                if old_text not in content:
                    return {
                        "success": False,
                        "error": f"Text not found: {old_text[:50]}...",
                    }

                new_content = content.replace(old_text, new_text)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {"success": True, "output": f"Edited {path}"}

            elif action == "append":
                with open(path, "a", encoding="utf-8") as f:
                    f.write(tool_input.get("content", ""))
                return {"success": True, "output": f"Appended to {path}"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_find_files(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Find files by pattern"""
        try:
            pattern = tool_input["pattern"]
            directory = tool_input.get("directory", ".")

            search_path = os.path.join(directory, pattern)
            files = glob.glob(search_path, recursive=True)
            files = [f for f in files if os.path.isfile(f)]

            return {
                "success": True,
                "output": f"Found {len(files)} files:\n"
                + "\n".join(files[:10])
                + (f"\n... and {len(files)-10} more" if len(files) > 10 else ""),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_search_in_files(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Search for text in files"""
        try:
            text = tool_input["text"]
            file_pattern = tool_input.get("file_pattern", "*.py")

            files = glob.glob(f"**/{file_pattern}", recursive=True)
            files = [f for f in files if os.path.isfile(f)]

            matches = []
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if text.lower() in line.lower():
                            matches.append(f"{file_path}:{i+1}: {line.strip()}")
                except:
                    continue

            return {
                "success": True,
                "output": f"Found {len(matches)} matches:\n" + "\n".join(matches[:10]),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_task_agent(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a focused sub-agent"""
        try:
            task_description = tool_input["task_description"]
            tools_needed = tool_input.get("tools_needed", ["file_editor", "bash"])

            print(f"🤖 Spawning sub-agent for: {task_description}")

            # Create a simplified sub-agent
            sub_config = Config(
                api_key=self.config.api_key,
                working_dir=self.config.working_dir,
                max_iterations=5,  # Limit sub-agent
                debug_mode=False,
                interactive_mode=False,  # Sub-agents are non-interactive
            )

            # Filter tools for sub-agent
            sub_tools = [
                t
                for t in self.tools
                if t["name"] in tools_needed or t["name"] == "bash"
            ]

            sub_agent = InteractiveSWEAgent.__new__(InteractiveSWEAgent)
            sub_agent.config = sub_config
            sub_agent.client = self.client
            sub_agent.tools = sub_tools
            sub_agent.conversation_history = []

            # Execute the sub-task
            result = sub_agent.execute_task(task_description)

            return {
                "success": result["success"],
                "output": f"Sub-agent completed in {result['iterations']} iterations. Result: {result.get('final_response', 'Task completed')[:200]}...",
            }

        except Exception as e:
            return {"success": False, "error": f"Sub-agent failed: {str(e)}"}

    def _get_user_input(self, question: str, context: str = "") -> str:
        """Get interactive user input"""
        print(f"\n❓ {question}")
        if context:
            print(f"💭 Context: {context}")

        user_response = input("Your response: ").strip()
        return user_response or "No response provided"

    def _display_tool_result(self, tool_name: str, result: Dict):
        """Display tool results with better formatting"""
        if result["success"]:
            print(f"  ✅ {tool_name} completed")
            if result.get("output") and result["output"] != "(No output)":
                output_preview = result["output"][:150]
                if len(result["output"]) > 150:
                    output_preview += "..."
                print(f"  📄 {output_preview}")
        else:
            print(f"  ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")

    def _truncate_conversation(self) -> List[Dict]:
        """Prevent context overflow"""
        if len(str(self.conversation_history)) > self.config.context_limit:
            # Keep first message (system prompt) and last few messages
            truncated = [self.conversation_history[0]]  # System prompt
            truncated.extend(self.conversation_history[-6:])  # Last 6 messages
            print("🔄 Truncated conversation to prevent context overflow")
            return truncated

        return self.conversation_history

    def _is_task_really_complete(self, response: str) -> bool:
        """More strict completion checking"""
        if not response:
            return False

        response_lower = response.lower()

        # Must have strong completion indicators AND not have failure indicators
        completion_words = ["completed", "finished", "done", "working", "success"]
        failure_words = ["error", "failed", "timeout", "issue", "problem"]

        has_completion = any(word in response_lower for word in completion_words)
        has_failure = any(word in response_lower for word in failure_words)

        return has_completion and not has_failure


def main():
    """Interactive CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Interactive SWE Agent V3")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument(
        "--max-iterations", type=int, default=15, help="Maximum iterations"
    )
    parser.add_argument(
        "--non-interactive", action="store_true", help="Disable interactive mode"
    )

    args = parser.parse_args()

    if args.task:
        task = " ".join(args.task)
    else:
        task = input("Enter task: ").strip()

    if not task:
        print("❌ No task provided")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return

    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        interactive_mode=not args.non_interactive,
    )

    try:
        agent = InteractiveSWEAgent(config)
        result = agent.execute_task(task)

        print(f"\n📊 Final Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
