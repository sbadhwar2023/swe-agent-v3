#!/usr/bin/env python3
"""
SWE Agent V2 - Complete Claude Code Equivalent
Real, intelligent, fast task execution with full tool suite
"""

import os
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# Import all tools
from tools import (
    read_file, write_file, edit_file, multi_edit,
    glob_files, ls_directory, grep_search, bash_command
)
from advanced_tools import todo_write, task_agent


@dataclass
class Config:
    """Agent configuration"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 20
    interactive_mode: bool = True
    debug_mode: bool = False


class SWEAgentV2:
    """Complete Claude Code equivalent - intelligent task execution"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=config.api_key,
            temperature=0
        )
        
        # Complete tool suite - Claude Code equivalent
        self.tools = [
            # File Operations
            read_file,
            write_file, 
            edit_file,
            multi_edit,
            
            # Search & Analysis
            glob_files,
            ls_directory, 
            grep_search,
            
            # Code Execution
            bash_command,
            
            # Task Management
            todo_write,
            task_agent  # Sub-agent spawning
        ]
        
        self.iteration_count = 0
        
        print(f"🚀 SWE Agent V2 - Claude Code Equivalent")
        print(f"📁 Working directory: {config.working_dir}")
        print(f"🔧 Tools available: {len(self.tools)}")
        print(f"   📄 File ops: read_file, write_file, edit_file, multi_edit")
        print(f"   🔍 Search: glob_files, ls_directory, grep_search") 
        print(f"   ⚡ Execution: bash_command")
        print(f"   📝 Management: todo_write, task_agent")
    
    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with full intelligence - Claude Code style"""
        
        print(f"\n📋 Task: {task}")
        print("🧠 Analyzing with full intelligence...")
        
        # Build intelligent system prompt
        system_prompt = f"""You are SWE Agent V2, an intelligent software engineering assistant equivalent to Claude Code.

TASK: {task}
WORKING DIRECTORY: {self.config.working_dir}

AVAILABLE TOOLS:
📄 File Operations:
- read_file(file_path, offset?, limit?) - Read files with optional line ranges
- write_file(file_path, content) - Create new files
- edit_file(file_path, old_string, new_string, replace_all?) - Modify existing files  
- multi_edit(file_path, edits) - Apply multiple edits atomically

🔍 Search & Analysis:
- glob_files(pattern, path?, sort_by_time?) - Advanced pattern matching
- ls_directory(path?, ignore?) - List contents with filtering
- grep_search(pattern, file_path?, path?, file_glob?, context_lines?, case_insensitive?) - Search within files

⚡ Code Execution:
- bash_command(command, working_dir?, timeout?) - Execute shell commands

📝 Task Management:
- todo_write(todos) - Create and track task lists for complex work
- task_agent(description, agent_type?, context?) - Spawn specialized sub-agents

INTELLIGENCE RULES:
1. **Analyze First**: Understand what needs to be done
2. **Use Right Tools**: Match tool capabilities to task requirements  
3. **Work Systematically**: For complex tasks, use todo_write to plan
4. **Delegate Complex Searches**: Use task_agent for focused work
5. **Be Thorough**: Actually complete the entire task
6. **Verify Results**: Check your work

EXAMPLES:
- Simple file tasks: Use file operations directly
- Complex projects: Use todo_write + multiple tools
- Large codebases: Use task_agent for analysis
- Multi-step workflows: Plan with todos, execute systematically

Execute this task completely and intelligently. Continue until fully done."""

        # Initialize conversation
        messages = [HumanMessage(content=system_prompt)]
        self.iteration_count = 0
        tools_used = []
        
        while self.iteration_count < self.config.max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {self.iteration_count + 1}")
                
                # Get LLM response with tools
                response = self.llm.bind_tools(self.tools).invoke(messages)
                # Clean up trailing whitespace to avoid API errors
                if hasattr(response, 'content') and response.content and isinstance(response.content, str):
                    response.content = response.content.rstrip()
                messages.append(response)
                
                # Execute tool calls if any
                if response.tool_calls:
                    print(f"🔧 Using tools: {[call['name'] for call in response.tool_calls]}")
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']
                        
                        if self.config.debug_mode:
                            print(f"   🔧 {tool_name}({', '.join(f'{k}={v}' for k, v in tool_args.items())})")
                        
                        # Find and execute tool
                        tool_func = next((t for t in self.tools if t.name == tool_name), None)
                        if tool_func:
                            try:
                                result = tool_func.invoke(tool_args)
                                tools_used.append({
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "success": result.get('success', True),
                                    "iteration": self.iteration_count + 1
                                })
                                
                                # Show result summary
                                if result.get('success'):
                                    if tool_name == 'write_file':
                                        print(f"   ✅ Created {tool_args['file_path']} ({result.get('size', 0)} chars)")
                                    elif tool_name == 'bash_command':
                                        print(f"   ✅ Executed: {tool_args['command']}")
                                    elif tool_name == 'grep_search':
                                        print(f"   ✅ Found {result.get('total_matches', 0)} matches")
                                    elif tool_name == 'task_agent':
                                        print(f"   ✅ Sub-agent completed with {result.get('tool_calls', 0)} tool calls")
                                    elif tool_name == 'todo_write':
                                        print(f"   ✅ Updated {result.get('updated_todos', 0)} todos")
                                    else:
                                        print(f"   ✅ {tool_name} completed")
                                else:
                                    print(f"   ❌ {tool_name} failed: {result.get('error', 'Unknown error')}")
                                
                                # Add tool result to conversation
                                messages.append(ToolMessage(
                                    content=json.dumps(result, indent=2),
                                    tool_call_id=tool_call['id']
                                ))
                                
                            except Exception as e:
                                error_msg = f"Tool execution error: {str(e)}"
                                print(f"   ❌ {tool_name} error: {str(e)}")
                                messages.append(ToolMessage(
                                    content=json.dumps({"success": False, "error": error_msg}),
                                    tool_call_id=tool_call['id']
                                ))
                        else:
                            print(f"   ❌ Unknown tool: {tool_name}")
                    
                    # Get follow-up response after tool execution
                    follow_up = self.llm.invoke(messages)
                    # Clean up trailing whitespace to avoid API errors
                    if hasattr(follow_up, 'content') and follow_up.content and isinstance(follow_up.content, str):
                        follow_up.content = follow_up.content.rstrip()
                    messages.append(follow_up)
                    
                    # Check if task appears complete
                    if self._is_task_complete(follow_up.content):
                        print("✅ Task completed successfully!")
                        break
                        
                else:
                    # No tool calls - task might be complete or need clarification
                    content = response.content.rstrip() if response.content else ""
                    if self._is_task_complete(content):
                        print("✅ Task completed!")
                        break
                    else:
                        print("ℹ️ No more tool calls needed")
                        break
                
                self.iteration_count += 1
                
            except Exception as e:
                print(f"❌ Error in iteration {self.iteration_count + 1}: {str(e)}")
                break
        
        # Generate final result
        final_message = messages[-1] if messages else None
        final_response = final_message.content if final_message else "No response generated"
        
        return {
            "task": task,
            "completed": True,
            "iterations": self.iteration_count,
            "tools_used": len(tools_used),
            "tool_details": tools_used,
            "final_response": final_response,
            "success": self.iteration_count < self.config.max_iterations
        }
    
    def _is_task_complete(self, response: str) -> bool:
        """Intelligent completion detection"""
        if not response:
            return False
        
        response_lower = response.lower()
        
        # Strong completion indicators
        strong_indicators = [
            "task completed", "task is complete", "successfully completed",
            "finished", "done", "all set", "ready to use", "implementation complete"
        ]
        
        # Weak completion indicators (need context)
        weak_indicators = [
            "completed", "created successfully", "working correctly"
        ]
        
        # Check for strong indicators
        if any(indicator in response_lower for indicator in strong_indicators):
            return True
        
        # Check for weak indicators with context
        if any(indicator in response_lower for indicator in weak_indicators):
            # Make sure it's not just about one step
            if not any(word in response_lower for word in ["next", "now", "then", "still need"]):
                return True
        
        return False


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SWE Agent V2 - Claude Code Equivalent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=20, help="Maximum iterations")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--non-interactive", action="store_true", help="Disable interactive mode")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    
    # Get task
    if args.task:
        task = " ".join(args.task)
    else:
        if args.non_interactive:
            print("❌ No task provided in non-interactive mode")
            sys.exit(1)
        task = input("Enter task: ").strip()
    
    if not task:
        print("❌ No task provided")
        sys.exit(1)
    
    # Create configuration
    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        interactive_mode=not args.non_interactive,
        debug_mode=args.debug
    )
    
    # Change to working directory
    if args.working_dir != ".":
        os.chdir(args.working_dir)
    
    # Create and run agent
    try:
        agent = SWEAgentV2(config)
        result = agent.execute_task(task)
        
        # Display results
        print(f"\n📊 Execution Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔧 Tools used: {result['tools_used']}")
        print(f"🔄 Iterations: {result['iterations']}")
        
        if config.debug_mode and result['tool_details']:
            print(f"\n🔍 Tool Details:")
            for tool in result['tool_details']:
                status = "✅" if tool['success'] else "❌"
                print(f"  {status} {tool['tool']} (iteration {tool['iteration']})")
        
        print(f"\n📄 Final Response:")
        print("-" * 60)
        print(result['final_response'])
        
    except KeyboardInterrupt:
        print("\n👋 Execution interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if config.debug_mode:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()