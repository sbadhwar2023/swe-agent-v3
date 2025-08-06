"""
SWE Agent V3 Fixed - Minimal, robust version
Fixes context overflow and tool execution issues
"""

import os
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class Config:
    """Minimal configuration"""

    api_key: str
    working_dir: str = "."
    max_iterations: int = 12
    interactive_mode: bool = True


class FixedSWEAgent:
    """Minimal, robust SWE agent that actually works"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)

        # Minimal tool set to prevent context overflow
        self.tools = [
            {
                "name": "bash",
                "description": "Execute bash commands",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute",
                        }
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "create_file",
                "description": "Create a new file with content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "content": {"type": "string", "description": "File content"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "read_file",
                "description": "Read file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "ask_user",
                "description": "Ask user for input when stuck or need clarification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Question to ask user",
                        }
                    },
                    "required": ["question"],
                },
            },
        ]

        if config.working_dir != ".":
            os.chdir(config.working_dir)

        print(f"🚀 Fixed SWE Agent V3 - Minimal & Robust")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"🔧 Tools: bash, create_file, read_file, ask_user")

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with minimal context and robust error handling"""

        print(f"\n📋 Task: {task}")

        # Very concise system prompt
        system_prompt = f"""You are a software engineering assistant. 

Tools available:
- bash: Execute shell commands 
- create_file: Create files with content
- read_file: Read file contents
- ask_user: Ask user for help when stuck

Working directory: {os.getcwd()}

IMPORTANT RULES:
1. Always provide valid file paths (never empty strings)
2. If a command fails, use ask_user to get guidance
3. Test your work by running the actual application
4. Don't claim success until you verify it works

Task: {task}"""

        messages = [{"role": "user", "content": system_prompt}]

        iteration = 0

        while iteration < self.config.max_iterations:
            try:
                print(f"\n🔍 Iteration {iteration + 1}")

                # Keep only recent messages to prevent context overflow
                if len(messages) > 8:  # Keep system + last 7 messages
                    messages = [messages[0]] + messages[-7:]
                    print("🔄 Trimmed conversation history")

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,  # Reduce token limit
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

                            # Execute tool with validation
                            result = self._execute_tool_with_validation(
                                tool_name, tool_input
                            )

                            # Handle ask_user specially
                            if (
                                tool_name == "ask_user"
                                and result["success"]
                                and self.config.interactive_mode
                            ):
                                user_response = input(
                                    f"\n❓ {tool_input['question']}\nYour response: "
                                ).strip()
                                result["output"] = (
                                    user_response or "No response provided"
                                )

                            self._display_result(tool_name, result)

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result["output"]
                                    if result["success"]
                                    else f"Error: {result.get('error', 'Unknown error')}",
                                }
                            )

                    messages.append({"role": "user", "content": tool_results})

                else:
                    # No tools - check completion
                    final_response = (
                        response.content[0].text if response.content else ""
                    )

                    if self.config.interactive_mode:
                        print(f"\n💭 Agent response: {final_response}")
                        user_input = (
                            input("\n❓ Is the task complete? (y/n/continue): ")
                            .strip()
                            .lower()
                        )

                        if user_input == "y":
                            print("✅ Task completed!")
                            return {
                                "success": True,
                                "iterations": iteration + 1,
                                "final_response": final_response,
                            }
                        elif user_input == "continue":
                            messages.append(
                                {
                                    "role": "user",
                                    "content": "Please continue working on the task.",
                                }
                            )
                        else:
                            feedback = input("What needs to be done? ")
                            messages.append(
                                {
                                    "role": "user",
                                    "content": f"User feedback: {feedback}",
                                }
                            )
                    else:
                        # Non-interactive - trust the agent
                        return {
                            "success": True,
                            "iterations": iteration + 1,
                            "final_response": final_response,
                        }

                iteration += 1

            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")

                if self.config.interactive_mode:
                    user_input = (
                        input(f"\n❓ Error occurred: {e}\nContinue anyway? (y/n): ")
                        .strip()
                        .lower()
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
                            "content": f"Error occurred: {e}. Please try a different approach.",
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

    def _execute_tool_with_validation(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tools with proper validation"""

        try:
            # Validate inputs before execution
            if tool_name in ["create_file", "read_file"] and not tool_input.get("path"):
                return {"success": False, "error": "File path cannot be empty"}

            if tool_name == "bash" and not tool_input.get("command"):
                return {"success": False, "error": "Command cannot be empty"}

            if tool_name == "bash":
                return self._execute_bash(tool_input["command"])

            elif tool_name == "create_file":
                return self._create_file(
                    tool_input["path"], tool_input.get("content", "")
                )

            elif tool_name == "read_file":
                return self._read_file(tool_input["path"])

            elif tool_name == "ask_user":
                return {"success": True, "output": "User input requested"}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    def _execute_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash command with proper error handling"""
        try:
            print(f"  🔧 Running: {command}")

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,  # Reasonable timeout
                cwd=os.getcwd(),
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output or "(No output)",
                "returncode": result.returncode,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 15 seconds"}
        except Exception as e:
            return {"success": False, "error": f"Command failed: {str(e)}"}

    def _create_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create file with proper error handling"""
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return {"success": True, "output": f"Created {path} ({len(content)} chars)"}

        except Exception as e:
            return {"success": False, "error": f"Failed to create {path}: {str(e)}"}

    def _read_file(self, path: str) -> Dict[str, Any]:
        """Read file with proper error handling"""
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Truncate very long files
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"

            return {"success": True, "output": content}

        except Exception as e:
            return {"success": False, "error": f"Failed to read {path}: {str(e)}"}

    def _display_result(self, tool_name: str, result: Dict):
        """Display tool results clearly"""
        if result["success"]:
            print(f"  ✅ {tool_name} succeeded")
            if result.get("output") and result["output"] != "(No output)":
                # Show first line of output
                first_line = result["output"].split("\n")[0]
                print(f"  📄 {first_line[:100]}...")
        else:
            print(f"  ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")
            # Also show stderr if available for bash commands
            if tool_name == "bash" and result.get("stderr"):
                print(f"  📄 STDERR: {result['stderr'][:100]}...")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Fixed SWE Agent V3")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=12, help="Max iterations")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Disable user prompts"
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
        agent = FixedSWEAgent(config)
        result = agent.execute_task(task)

        print(f"\n📊 Final Result:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")

        if not result["success"] and "error" in result:
            print(f"❌ Error: {result['error']}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
