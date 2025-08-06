"""
SWE Agent V3 - True Claude Code equivalent
Working implementation that actually functions like Claude Code
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class Config:
    """Agent configuration"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 15
    debug_mode: bool = False


def create_tool_schema():
    """Create Anthropic tool schema for Claude's native tool calling"""
    return [
        {
            "name": "bash",
            "description": "Execute bash commands",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"}
                },
                "required": ["command"]
            }
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
                        "description": "The command to execute"
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {"type": "string", "description": "Content for create command"},
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"}
                },
                "required": ["command", "path"]
            }
        }
    ]


class SWEAgent:
    """True Claude Code equivalent - working SWE agent"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_tool_schema()
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
        
        print(f"🚀 SWE Agent V3 - Ready for software engineering tasks")
        print(f"📁 Working directory: {os.getcwd()}")
    
    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute a software engineering task"""
        
        print(f"\n📋 Task: {task}")
        
        # Create system prompt like Claude Code
        system_prompt = f"""You are a helpful AI assistant that can execute software engineering tasks.

You have access to these tools:
1. bash - Execute shell commands
2. str_replace_editor - Create, read, and edit files

Working directory: {os.getcwd()}

For file operations:
- Use str_replace_editor with command="create" to create new files
- Use str_replace_editor with command="view" to read files  
- Use str_replace_editor with command="str_replace" to edit files

For shell operations:
- Use bash to run commands like mkdir, ls, git, npm, etc.

Be systematic and thorough. Execute the task step by step."""

        messages = [
            {"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}
        ]
        
        iteration = 0
        max_iterations = self.config.max_iterations
        
        while iteration < max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {iteration + 1}")
                
                # Get response with tools
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages,
                    tools=self.tools
                )
                
                # Add assistant response to conversation
                messages.append({"role": "assistant", "content": response.content})
                
                # Check for tool use
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id
                            
                            print(f"🔧 Using {tool_name}")
                            
                            # Execute tool
                            result = self._execute_tool(tool_name, tool_input)
                            
                            # Display result
                            if result["success"]:
                                print(f"  ✅ {tool_name} completed")
                                if result.get("output") and self.config.debug_mode:
                                    print(f"  📄 Output: {result['output'][:200]}...")
                            else:
                                print(f"  ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result["output"] if result["success"] else f"Error: {result.get('error', 'Unknown error')}"
                            })
                    
                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                    
                else:
                    # No tool use - task might be complete
                    final_response = response.content[0].text if response.content else "Task completed"
                    print("✅ Task completed")
                    
                    return {
                        "success": True,
                        "iterations": iteration + 1,
                        "final_response": final_response,
                        "messages": messages
                    }
                
                iteration += 1
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")
                return {
                    "success": False,
                    "iterations": iteration + 1,
                    "error": str(e),
                    "messages": messages
                }
        
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max iterations reached",
            "messages": messages
        }
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return result"""
        
        try:
            if tool_name == "bash":
                return self._execute_bash(tool_input["command"])
            
            elif tool_name == "str_replace_editor":
                command = tool_input["command"]
                path = tool_input["path"]
                
                if command == "create":
                    return self._create_file(path, tool_input.get("file_text", ""))
                elif command == "view":
                    return self._view_file(path)
                elif command == "str_replace":
                    return self._replace_in_file(path, tool_input["old_str"], tool_input["new_str"])
                else:
                    return {"success": False, "error": f"Unknown str_replace_editor command: {command}"}
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash command"""
        import subprocess
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create a new file"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "output": f"Created file: {path} ({len(content)} characters)"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _view_file(self, path: str) -> Dict[str, Any]:
        """Read file contents"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "output": content
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _replace_in_file(self, path: str, old_str: str, new_str: str) -> Dict[str, Any]:
        """Replace text in file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_str not in content:
                return {"success": False, "error": f"String not found in file: {old_str[:50]}..."}
            
            new_content = content.replace(old_str, new_str)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "output": f"Replaced text in {path}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SWE Agent V3 - Software Engineering Assistant")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=15, help="Maximum iterations")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
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
    
    # Create config and agent
    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug
    )
    
    try:
        agent = SWEAgent(config)
        result = agent.execute_task(task)
        
        print(f"\n📊 Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")
        
        if not result['success'] and 'error' in result:
            print(f"❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()