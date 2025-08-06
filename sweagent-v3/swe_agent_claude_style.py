"""
SWE Agent V3 Claude Style - Exactly like Claude Code
Smart command splitting, proper timeouts, step-by-step execution
"""

import os
import json
import glob
import re
import subprocess
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class Config:
    """Claude-style configuration"""

    api_key: str
    working_dir: str = "."
    max_iterations: int = 25
    debug_mode: bool = True
    interactive_mode: bool = True


def create_claude_tools():
    """Tools that match Claude Code exactly"""
    return [
        {
            "name": "bash",
            "description": "Execute single bash commands (avoid chaining with &&)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Single bash command to execute",
                    }
                },
                "required": ["command"],
            },
        },
        {
            "name": "str_replace_editor",
            "description": "Create, read, and edit files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "view"],
                        "description": "File operation",
                    },
                    "path": {"type": "string", "description": "File path"},
                    "file_text": {
                        "type": "string",
                        "description": "Content for create",
                    },
                    "old_str": {"type": "string", "description": "Text to replace"},
                    "new_str": {"type": "string", "description": "Replacement text"},
                },
                "required": ["command", "path"],
            },
        },
        {
            "name": "ask_user_step",
            "description": "Ask user before proceeding to next step",
            "input_schema": {
                "type": "object",
                "properties": {
                    "current_step": {
                        "type": "string",
                        "description": "What was just completed",
                    },
                    "next_step": {
                        "type": "string",
                        "description": "What you want to do next",
                    },
                    "context": {"type": "string", "description": "Why asking user"},
                },
                "required": ["current_step", "next_step"],
            },
        },
    ]


class ClaudeStyleAgent:
    """Agent that behaves exactly like Claude Code"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_claude_tools()

        if config.working_dir != ".":
            os.chdir(config.working_dir)

        print(f"🚀 Claude Style SWE Agent - Exact Claude Code Behavior")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"🔧 Tools: bash (smart), str_replace_editor, ask_user_step")
        print(f"⚡ Smart command splitting, proper timeouts, step-by-step")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute with Claude Code patterns"""

        print(f"\n📋 Task: {task}")

        system_prompt = f"""You are a software engineering assistant that works EXACTLY like Claude Code.

CLAUDE CODE PRINCIPLES:
1. **Work step by step** - Complete one clear step at a time
2. **Ask before complex operations** - Use ask_user_step before long-running commands
3. **Single commands only** - Never chain commands with && or ;
4. **Show progress** - Execute each step separately so user sees progress
5. **Smart about installs** - Break pip installs into individual packages when possible

TOOLS:
- bash: Execute ONE command at a time (no chaining)
- str_replace_editor: File operations (create/view/edit)  
- ask_user_step: Ask user before proceeding to next step

WORKFLOW EXAMPLE:
1. Create project structure
2. ask_user_step: "Created project structure. Should I create the virtual environment?"
3. bash: python -m venv venv_name  
4. ask_user_step: "Virtual environment created. Should I install packages?"
5. bash: pip install flask (one package)
6. bash: pip install requests (another package)
7. Continue step by step...

RULES:
- NEVER use && or ; in bash commands
- Ask user before any install/download operations
- Show each step completion
- Break complex operations into simple steps

Working directory: {os.getcwd()}
Task: {task}"""

        messages = [{"role": "user", "content": system_prompt}]

        iteration = 0

        while iteration < self.config.max_iterations:
            try:
                print(f"\n🔍 Iteration {iteration + 1}")

                # Keep conversation reasonable size
                if len(str(messages)) > 10000:
                    messages = [messages[0]] + messages[-10:]
                    print("🔄 Trimmed conversation")

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2500,
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

                            print(f"🔧 {tool_name}")

                            # Execute with Claude Code behavior
                            result = self._execute_claude_tool(tool_name, tool_input)

                            # Handle user interaction
                            if (
                                tool_name == "ask_user_step"
                                and result["success"]
                                and self.config.interactive_mode
                            ):
                                user_response = self._handle_step_question(tool_input)
                                result["output"] = user_response

                            self._display_claude_result(tool_name, result)

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
                    # No tools - check completion
                    final_response = (
                        response.content[0].text if response.content else ""
                    )

                    print(f"\n💭 {final_response}")

                    if self.config.interactive_mode:
                        user_input = (
                            input("\n❓ Task complete? (y/n/continue): ").strip().lower()
                        )

                        if user_input == "y":
                            print("✅ Task completed!")
                            return {
                                "success": True,
                                "iterations": iteration + 1,
                                "final_response": final_response,
                            }
                        elif user_input == "n":
                            feedback = input("What's missing? ")
                            messages.append(
                                {"role": "user", "content": f"Not complete: {feedback}"}
                            )
                        else:
                            messages.append(
                                {"role": "user", "content": "Continue working."}
                            )
                    else:
                        return {
                            "success": True,
                            "iterations": iteration + 1,
                            "final_response": final_response,
                        }

                iteration += 1

            except Exception as e:
                print(f"❌ Error: {e}")

                if self.config.interactive_mode:
                    user_input = input("Continue? (y/n): ").strip().lower()
                    if user_input != "y":
                        return {
                            "success": False,
                            "iterations": iteration + 1,
                            "error": str(e),
                        }

                    messages.append(
                        {
                            "role": "user",
                            "content": f"Error occurred: {e}. Please continue with a different approach.",
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

    def _execute_claude_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tools with Claude Code behavior"""

        try:
            if tool_name == "bash":
                return self._execute_claude_bash(tool_input["command"])

            elif tool_name == "str_replace_editor":
                return self._execute_file_operation(tool_input)

            elif tool_name == "ask_user_step":
                return {"success": True, "output": "User step confirmation requested"}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_claude_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash with Claude Code timeouts and behavior"""
        try:
            print(f"⏺ Bash({command})")

            # Detect command type and set appropriate timeout
            if any(
                keyword in command.lower() for keyword in ["pip install", "npm install"]
            ):
                timeout = 180  # 3 minutes for installs
                print(f"  ⎿  Installing packages (may take up to 3 minutes)...")
            elif "venv" in command.lower() or "virtualenv" in command.lower():
                timeout = 60  # 1 minute for venv
            elif any(
                keyword in command.lower() for keyword in ["git clone", "curl", "wget"]
            ):
                timeout = 120  # 2 minutes for downloads
            else:
                timeout = 30  # 30s for regular commands

            # Execute command
            start_time = time.time()
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            end_time = time.time()

            # Prepare output like Claude Code
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            # Show execution time for long commands
            exec_time = end_time - start_time
            if exec_time > 5:
                print(f"  ⎿  Completed in {exec_time:.1f}s")

            return {
                "success": result.returncode == 0,
                "output": output or "(No content)",
                "returncode": result.returncode,
                "execution_time": exec_time,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s. This might be normal for large installs - try breaking into smaller steps.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_file_operation(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """File operations like Claude Code"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                # Create directory if needed
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                content = tool_input.get("file_text", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"⏺ Write({path})")
                print(f"  ⎿  Wrote {len(content.splitlines())} lines to {path}")

                return {
                    "success": True,
                    "output": f"Wrote {len(content.splitlines())} lines to {path}",
                }

            elif command == "view":
                if not os.path.exists(path):
                    return {"success": False, "error": f"File not found: {path}"}

                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Show preview like Claude Code
                lines = content.splitlines()
                preview = "\n".join(lines[:20])
                if len(lines) > 20:
                    preview += f"\n... ({len(lines)} total lines)"

                print(f"⏺ Read({path})")
                print(f"  ⎿  Read {len(lines)} lines from {path}")

                return {"success": True, "output": preview}

            elif command == "str_replace":
                if not os.path.exists(path):
                    return {"success": False, "error": f"File not found: {path}"}

                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]

                if old_str not in content:
                    return {"success": False, "error": f"Text not found in {path}"}

                new_content = content.replace(old_str, new_str)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                print(f"⏺ Edit({path})")
                print(f"  ⎿  Made replacement in {path}")

                return {"success": True, "output": f"Made replacement in {path}"}

            else:
                return {"success": False, "error": f"Unknown file command: {command}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_step_question(self, tool_input: Dict[str, Any]) -> str:
        """Handle step-by-step questions like Claude Code"""
        current_step = tool_input["current_step"]
        next_step = tool_input["next_step"]
        context = tool_input.get("context", "")

        print(f"\n📋 Completed: {current_step}")
        if context:
            print(f"💭 Context: {context}")
        print(f"🔜 Next: {next_step}")

        user_response = input("\n❓ Proceed? (y/n/modify): ").strip().lower()

        if user_response == "y":
            return f"User confirmed: proceed with {next_step}"
        elif user_response == "n":
            reason = input("Why not? ")
            return f"User declined: {reason}. Please adjust approach."
        else:
            modification = input("How should I modify the approach? ")
            return f"User wants modification: {modification}"

    def _display_claude_result(self, tool_name: str, result: Dict):
        """Display results exactly like Claude Code"""
        if result["success"]:
            if tool_name == "bash":
                # Already displayed in execute function
                if result.get("returncode") == 0:
                    pass  # Success already shown
                else:
                    print(f"  ⎿  ❌ Exit code: {result.get('returncode', 'unknown')}")
            elif tool_name == "str_replace_editor":
                # Already displayed in execute function
                pass
            elif tool_name == "ask_user_step":
                print("  ⎿  ✅ Got user confirmation")
        else:
            print(f"  ⎿  ❌ {result.get('error', 'Unknown error')}")


def main():
    """Claude-style CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Style SWE Agent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=25, help="Max iterations")
    parser.add_argument(
        "--non-interactive", action="store_true", help="No user interaction"
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
        agent = ClaudeStyleAgent(config)
        result = agent.execute_task(task)

        print(f"\n📊 Final Result:")
        print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
        print(f"Iterations: {result['iterations']}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
