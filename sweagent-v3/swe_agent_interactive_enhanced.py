"""
SWE Agent V3 Interactive Enhanced - Claude Code style interaction
Combines enhanced tools with Claude Code's interactive feedback patterns
"""

import os
import json
import glob
import re
import subprocess
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class Config:
    """Enhanced interactive configuration"""

    api_key: str
    working_dir: str = "."
    max_iterations: int = 20
    debug_mode: bool = False
    interactive_mode: bool = True


def create_interactive_tool_schema():
    """Enhanced tools with interactive feedback"""
    return [
        # Core execution
        {
            "name": "bash",
            "description": "Execute bash commands",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    }
                },
                "required": ["command"],
            },
        },
        # File operations
        {
            "name": "str_replace_editor",
            "description": "Create, read, and edit files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "view"],
                        "description": "The command to execute",
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {
                        "type": "string",
                        "description": "Content for create command",
                    },
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                },
                "required": ["command", "path"],
            },
        },
        # Search tools
        {
            "name": "glob_search",
            "description": "Find files using patterns",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern"},
                    "path": {
                        "type": "string",
                        "description": "Base path",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "grep_search",
            "description": "Search for patterns within files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "path": {
                        "type": "string",
                        "description": "Path to search",
                        "default": ".",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern",
                        "default": "*",
                    },
                },
                "required": ["pattern"],
            },
        },
        # Interactive todo management
        {
            "name": "todo_write",
            "description": "Create and update task lists with interactive feedback",
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
        # Ask user for feedback
        {
            "name": "ask_user_feedback",
            "description": "Ask user to confirm completion or get feedback on current progress",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_description": {
                        "type": "string",
                        "description": "What step was just completed",
                    },
                    "question": {
                        "type": "string",
                        "description": "Specific question to ask user",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about current state",
                    },
                },
                "required": ["step_description", "question"],
            },
        },
        # Sub-agent spawning
        {
            "name": "task_agent",
            "description": "Launch sub-agents for focused tasks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Task for sub-agent",
                    },
                    "agent_type": {
                        "type": "string",
                        "enum": ["search", "analysis", "coding", "debugging"],
                        "default": "coding",
                    },
                },
                "required": ["task_description"],
            },
        },
    ]


class InteractiveEnhancedAgent:
    """Enhanced agent with Claude Code style interaction patterns"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_interactive_tool_schema()
        self.current_todos = {}

        if config.working_dir != ".":
            os.chdir(config.working_dir)

        print(f"🚀 Interactive Enhanced SWE Agent - Claude Code Style")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"💬 Interactive mode: {'ON' if config.interactive_mode else 'OFF'}")
        print(f"🔧 Enhanced tools: bash, str_replace_editor, glob_search, grep_search")
        print(f"📝 Management: todo_write, ask_user_feedback, task_agent")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute with Claude Code interaction patterns"""

        print(f"\n📋 Task: {task}")

        system_prompt = f"""You are an interactive software engineering assistant that works like Claude Code.

INTERACTION PATTERNS:
1. **Break down complex tasks** - Use todo_write to create step-by-step plans
2. **Work incrementally** - Complete one step at a time
3. **Get user feedback** - After each major step, use ask_user_feedback to confirm completion
4. **Update progress** - Keep todos updated based on user feedback
5. **Handle failures gracefully** - If something fails, ask user for guidance

AVAILABLE TOOLS:
- bash: Execute shell commands
- str_replace_editor: Create, read, edit files
- glob_search: Find files by patterns
- grep_search: Search text in files
- todo_write: Create/update task lists with progress tracking
- ask_user_feedback: Get user confirmation on step completion
- task_agent: Spawn focused sub-agents

WORKFLOW:
1. Start with todo_write to plan the task
2. Work on each todo item systematically  
3. After completing each step, use ask_user_feedback
4. Update todos based on feedback (completed/needs work)
5. Continue until all todos completed and user confirms

Working directory: {os.getcwd()}

Task: {task}"""

        messages = [{"role": "user", "content": system_prompt}]

        iteration = 0

        while iteration < self.config.max_iterations:
            try:
                print(f"\n🔍 Iteration {iteration + 1}")

                # Manage conversation length
                if len(str(messages)) > 8000:  # Rough character count
                    messages = [messages[0]] + messages[-8:]  # Keep system + last 8
                    print("🔄 Trimmed conversation to prevent overflow")

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=3000,
                    messages=messages,
                    tools=self.tools,
                )

                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "tool_use":
                    tool_results = []

                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            print(f"🔧 Using {tool_name}")

                            # Execute tool
                            result = self._execute_enhanced_tool(tool_name, tool_input)

                            # Handle interactive feedback
                            if (
                                tool_name == "ask_user_feedback"
                                and result["success"]
                                and self.config.interactive_mode
                            ):
                                user_response = self._get_user_feedback(tool_input)
                                result["output"] = user_response

                            self._display_tool_result(tool_name, result)

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result["output"]
                                    if result["success"]
                                    else f"Error: {result.get('error', 'Failed')}",
                                }
                            )

                    messages.append({"role": "user", "content": tool_results})

                else:
                    # No tools - might be complete
                    final_response = (
                        response.content[0].text if response.content else ""
                    )

                    print(f"\n💭 Agent says: {final_response}")

                    if self.config.interactive_mode:
                        user_input = (
                            input("\n❓ Overall task complete? (y/n/continue): ")
                            .strip()
                            .lower()
                        )

                        if user_input == "y":
                            print("✅ Task completed with user confirmation!")
                            return {
                                "success": True,
                                "iterations": iteration + 1,
                                "final_response": final_response,
                            }
                        elif user_input == "n":
                            feedback = input("What still needs to be done? ")
                            messages.append(
                                {
                                    "role": "user",
                                    "content": f"Task not complete. User says: {feedback}. Please address this and continue.",
                                }
                            )
                        else:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": "Please continue working on the task.",
                                }
                            )
                    else:
                        return {
                            "success": True,
                            "iterations": iteration + 1,
                            "final_response": final_response,
                        }

                iteration += 1

            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")

                if self.config.interactive_mode:
                    print(f"Error details: {str(e)}")
                    user_input = (
                        input("Continue despite error? (y/n): ").strip().lower()
                    )
                    if user_input != "y":
                        return {
                            "success": False,
                            "iterations": iteration + 1,
                            "error": str(e),
                        }

                    messages.append(
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

        return {
            "success": False,
            "iterations": self.config.max_iterations,
            "error": "Max iterations reached",
        }

    def _execute_enhanced_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute enhanced tools"""

        try:
            if tool_name == "bash":
                return self._execute_bash(tool_input["command"])

            elif tool_name == "str_replace_editor":
                return self._execute_str_replace_editor(tool_input)

            elif tool_name == "glob_search":
                return self._execute_glob_search(tool_input)

            elif tool_name == "grep_search":
                return self._execute_grep_search(tool_input)

            elif tool_name == "todo_write":
                return self._execute_todo_write(tool_input)

            elif tool_name == "ask_user_feedback":
                return {"success": True, "output": "User feedback requested"}

            elif tool_name == "task_agent":
                return self._execute_task_agent(tool_input)

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash command"""
        try:
            print(f"  🔧 Running: {command}")

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=20
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output or "(No output)",
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 20s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_str_replace_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """File operations"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                content = tool_input.get("file_text", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "output": f"Created {path}"}

            elif command == "view":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Truncate long files
                if len(content) > 1000:
                    content = content[:1000] + "\n...(truncated)"
                return {"success": True, "output": content}

            elif command == "str_replace":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]

                if old_str not in content:
                    return {"success": False, "error": f"Text not found in {path}"}

                new_content = content.replace(old_str, new_str)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {"success": True, "output": f"Updated {path}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_glob_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Find files by pattern"""
        try:
            pattern = tool_input["pattern"]
            base_path = tool_input.get("path", ".")

            search_pattern = os.path.join(base_path, "**", pattern)
            files = glob.glob(search_pattern, recursive=True)
            files = [f for f in files if os.path.isfile(f)]

            return {
                "success": True,
                "output": f"Found {len(files)} files:\n"
                + "\n".join(files[:10])
                + (f"\n...and {len(files)-10} more" if len(files) > 10 else ""),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_grep_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Search within files"""
        try:
            pattern = tool_input["pattern"]
            search_path = tool_input.get("path", ".")
            file_pattern = tool_input.get("file_pattern", "*")

            matches = []
            files = glob.glob(
                os.path.join(search_path, "**", file_pattern), recursive=True
            )
            files = [f for f in files if os.path.isfile(f)]

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if pattern.lower() in line.lower():
                            matches.append(f"{file_path}:{i+1}: {line.strip()}")
                            if len(matches) >= 20:  # Limit results
                                break
                except:
                    continue

            return {
                "success": True,
                "output": f"Found {len(matches)} matches:\n" + "\n".join(matches[:15]),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_todo_write(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Interactive todo management"""
        try:
            todos_data = tool_input["todos"]

            # Update internal state
            for todo in todos_data:
                self.current_todos[todo["id"]] = todo

            # Display like Claude Code
            output = "⏺ Update Todos\n"
            for todo in todos_data:
                status_symbol = {"pending": "☐", "in_progress": "🔄", "completed": "☒"}
                symbol = status_symbol.get(todo["status"], "☐")
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                priority = priority_emoji.get(todo["priority"], "")
                output += f"  ⎿  {symbol} {todo['content']} {priority}\n"

            print(output)  # Display immediately

            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_task_agent(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn sub-agent"""
        try:
            task_description = tool_input["task_description"]
            agent_type = tool_input.get("agent_type", "coding")

            print(f"🤖 Spawning {agent_type} sub-agent: {task_description}")

            # Simple sub-agent implementation
            sub_config = Config(
                api_key=self.config.api_key,
                max_iterations=5,
                interactive_mode=False,  # Sub-agents are non-interactive
            )

            # Create minimal sub-agent
            sub_agent = InteractiveEnhancedAgent.__new__(InteractiveEnhancedAgent)
            sub_agent.config = sub_config
            sub_agent.client = self.client
            sub_agent.tools = self.tools[:4]  # Basic tools only
            sub_agent.current_todos = {}

            result = sub_agent.execute_task(task_description)

            return {
                "success": result["success"],
                "output": f"Sub-agent completed in {result['iterations']} iterations",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_user_feedback(self, tool_input: Dict[str, Any]) -> str:
        """Get interactive user feedback like Claude Code"""
        step_description = tool_input["step_description"]
        question = tool_input["question"]
        context = tool_input.get("context", "")

        print(f"\n📋 Step completed: {step_description}")
        if context:
            print(f"💭 Context: {context}")
        print(f"❓ {question}")

        user_response = input("Your feedback (y/n/comments): ").strip()

        # Handle common responses
        if user_response.lower() == "y":
            return "User confirmed this step is complete. Proceed to next step."
        elif user_response.lower() == "n":
            additional = input("What needs to be fixed? ")
            return f"User says step is not complete. Issue: {additional}"
        else:
            return f"User feedback: {user_response}"

    def _display_tool_result(self, tool_name: str, result: Dict):
        """Display results like Claude Code"""
        if result["success"]:
            if tool_name == "todo_write":
                # Already displayed in execute function
                pass
            elif tool_name == "ask_user_feedback":
                print(f"  ✅ Got user feedback")
            else:
                print(f"  ✅ {tool_name} completed")
                if result.get("output") and len(result["output"]) > 0:
                    preview = result["output"][:100]
                    if len(result["output"]) > 100:
                        preview += "..."
                    print(f"  📄 {preview}")
        else:
            print(f"  ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")


def main():
    """Interactive enhanced CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Interactive Enhanced SWE Agent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=20, help="Max iterations")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Disable interaction"
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
        debug_mode=True,
    )

    try:
        agent = InteractiveEnhancedAgent(config)
        result = agent.execute_task(task)

        print(f"\n📊 Final Result:")
        print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
        print(f"Iterations: {result['iterations']}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
