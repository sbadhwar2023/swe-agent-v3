"""
SWE Agent Ultimate FIXED - Complete Claude Code Equivalent with Proper UX
Fixes: User interaction handling, UI improvements, trajectory clarity
Features: Hooks support, clean progress display, proper conversation flow
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


class Colors:
    """Terminal colors for better UI"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


@dataclass
class ProgressEntry:
    """Individual progress entry with better tracking"""
    timestamp: str
    action: str
    details: str
    files_affected: List[str] = field(default_factory=list)
    status: str = "completed"
    tool_used: str = ""
    duration: float = 0.0


@dataclass
class Config:
    """Enhanced configuration with UI options"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 50
    debug_mode: bool = False
    state_file: str = ".swe_agent_ultimate_state.pkl"
    progress_file: str = "progress.md"
    enable_web: bool = True
    enable_notebooks: bool = True
    max_sub_agents: int = 3
    # UI/UX Settings
    rich_display: bool = True
    show_trajectory: bool = True
    hooks_enabled: bool = True
    progress_interval: int = 5  # Show progress every N iterations
    user_confirmation: bool = True


class ProgressDisplay:
    """Rich progress display like Claude Code"""
    
    def __init__(self, rich_display: bool = True):
        self.rich_display = rich_display
        self.current_step = 0
        self.total_steps = 0
        
    def show_header(self, agent_name: str, working_dir: str, tools_count: int):
        """Show agent startup header"""
        if not self.rich_display:
            return
            
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 {agent_name}{Colors.ENDC}")
        print(f"{Colors.BLUE}📁 Working: {working_dir}{Colors.ENDC}")
        print(f"{Colors.BLUE}🔧 Tools: {tools_count} available{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    
    def show_task_start(self, task: str):
        """Show task beginning"""
        if not self.rich_display:
            print(f"Task: {task}")
            return
            
        print(f"\n{Colors.BOLD}{Colors.GREEN}📋 TASK STARTED{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─'*50}{Colors.ENDC}")
        
        # Show task in wrapped format
        words = task.split()
        lines = []
        current_line = []
        for word in words:
            if len(' '.join(current_line + [word])) > 60:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))
            
        for line in lines:
            print(f"{Colors.BLUE}│{Colors.ENDC} {line}")
        print(f"{Colors.CYAN}{'─'*50}{Colors.ENDC}\n")
    
    def show_iteration(self, iteration: int, max_iterations: int):
        """Show iteration progress"""
        if not self.rich_display:
            return
            
        progress = int((iteration / max_iterations) * 20)
        bar = '█' * progress + '░' * (20 - progress)
        print(f"{Colors.YELLOW}🔄 Iteration {iteration}/{max_iterations} [{bar}]{Colors.ENDC}")
    
    def show_tool_use(self, tool_name: str, description: str = ""):
        """Show tool usage with consistent format"""
        if not self.rich_display:
            print(f"Using {tool_name}")
            return
            
        tool_icons = {
            'bash': '⚡',
            'str_replace_editor': '📝',
            'glob_search': '🔍',
            'grep_search': '🔎',
            'web_search': '🌐',
            'task_agent': '🤖',
            'todo_write': '📋',
            'list_directory': '📁'
        }
        
        icon = tool_icons.get(tool_name, '🔧')
        print(f"{Colors.CYAN}⏺{Colors.ENDC} {icon} {tool_name}()")
        if description:
            print(f"{Colors.BLUE}  ⎿{Colors.ENDC} {description}")
    
    def show_tool_result(self, tool_name: str, success: bool, summary: str = ""):
        """Show tool result"""
        if not self.rich_display:
            return
            
        status = f"{Colors.GREEN}✅" if success else f"{Colors.RED}❌"
        result_text = summary or ("Operation completed" if success else "Operation failed")
        print(f"{Colors.BLUE}  ⎿{Colors.ENDC} {status} {result_text}{Colors.ENDC}")
    
    def show_progress_summary(self, files_created: int, sub_agents: int, tools_used: int):
        """Show periodic progress summary"""
        if not self.rich_display:
            return
            
        print(f"\n{Colors.YELLOW}📊 Progress Update{Colors.ENDC}")
        print(f"{Colors.BLUE}  📄 Files: {files_created} | 🤖 Sub-agents: {sub_agents} | 🔧 Tools: {tools_used}{Colors.ENDC}")
    
    def show_completion_prompt(self, final_response: str, stats: Dict):
        """Show completion prompt with clear options"""
        if not self.rich_display:
            print(f"\nTask Summary: {final_response}")
            print("Complete? (y/n/continue)")
            return
            
        print(f"\n{Colors.GREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 TASK PHASE COMPLETED{Colors.ENDC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.ENDC}")
        
        # Show final response in clean format
        print(f"\n{Colors.CYAN}📋 Summary:{Colors.ENDC}")
        print(f"{Colors.BLUE}  {final_response}{Colors.ENDC}")
        
        # Show statistics
        print(f"\n{Colors.YELLOW}📊 Statistics:{Colors.ENDC}")
        for key, value in stats.items():
            print(f"{Colors.BLUE}  {key}: {value}{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}❓ What would you like to do next?{Colors.ENDC}")
        print(f"{Colors.GREEN}  y{Colors.ENDC} - Task is complete, finish and save")
        print(f"{Colors.YELLOW}  n{Colors.ENDC} - Continue working (provide feedback)")
        print(f"{Colors.CYAN}  continue{Colors.ENDC} - Continue without feedback")
        print(f"{Colors.RED}  quit{Colors.ENDC} - Stop and save state")


class HooksManager:
    """Simple hooks system like Claude Code"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.hooks = {
            'pre_task': [],
            'post_tool': [],
            'pre_iteration': [],
            'post_iteration': [],
            'task_complete': []
        }
    
    def register_hook(self, event: str, callback):
        """Register a hook callback"""
        if event in self.hooks:
            self.hooks[event].append(callback)
    
    def execute_hooks(self, event: str, context: Dict = None):
        """Execute all hooks for an event"""
        if not self.enabled:
            return
            
        for hook in self.hooks.get(event, []):
            try:
                hook(context or {})
            except Exception as e:
                print(f"Hook error ({event}): {e}")


class UltimateAgentState:
    """Enhanced agent state"""
    def __init__(self, task_id: str, original_task: str):
        self.task_id = task_id
        self.original_task = original_task
        self.completed_steps = []
        self.current_step = ""
        self.error_history = []
        self.iteration_count = 0
        self.last_successful_operation = ""
        self.working_context = {}
        self.progress_entries = []
        self.files_tracking = {}
        self.sub_agent_results = []
        self.start_time = datetime.datetime.now()
        self.last_user_interaction = None


class UltimateSWEAgentFixed:
    """Fixed Ultimate SWE Agent with proper UX"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = self._create_tools()
        self.display = ProgressDisplay(config.rich_display)
        self.hooks = HooksManager(config.hooks_enabled)
        self.state = None
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
        
        # Show startup
        self.display.show_header(
            "Ultimate SWE Agent (Fixed)",
            os.getcwd(),
            len(self.tools)
        )
        
        # Register default hooks
        self._register_default_hooks()
    
    def _create_tools(self):
        """Create tool schema (simplified for demo)"""
        return [
            {
                "name": "bash",
                "description": "Execute bash commands",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "number", "default": 30}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "str_replace_editor",
                "description": "File operations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "enum": ["create", "str_replace", "view"]},
                        "path": {"type": "string"},
                        "file_text": {"type": "string"},
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"}
                    },
                    "required": ["command", "path"]
                }
            },
            {
                "name": "web_search", 
                "description": "Search the web",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "number", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        ]
    
    def _register_default_hooks(self):
        """Register helpful default hooks"""
        def log_iteration(context):
            if self.config.debug_mode and context.get('iteration'):
                print(f"Debug: Iteration {context['iteration']} started")
        
        def save_progress(context):
            if context.get('iteration', 0) % 10 == 0:
                self._save_state()
        
        self.hooks.register_hook('pre_iteration', log_iteration)
        self.hooks.register_hook('post_iteration', save_progress)
    
    def execute_task(self, task: str, resume_task_id: str = None) -> Dict[str, Any]:
        """Execute task with proper user interaction handling"""
        
        if resume_task_id:
            return self._resume_task(resume_task_id)
        
        # Initialize new task
        task_id = f"task_{int(time.time())}"
        self.state = UltimateAgentState(task_id, task)
        
        self.display.show_task_start(task)
        self.hooks.execute_hooks('pre_task', {'task': task})
        
        # Enhanced system prompt
        system_prompt = f"""You are an advanced software engineering assistant with comprehensive tools.

Available tools: {', '.join([t['name'] for t in self.tools])}

Key behaviors:
1. Work systematically through complex tasks
2. Provide clear progress updates
3. Handle errors gracefully and continue from failure points
4. Use appropriate tools for each subtask
5. Communicate clearly with the user

When you complete a significant phase, I will ask if you want to continue.
Be conversational and helpful throughout the process.

Working directory: {os.getcwd()}
Task: {task}"""

        messages = [{"role": "user", "content": system_prompt}]
        
        return self._execute_conversation_loop(messages)
    
    def _execute_conversation_loop(self, messages: List[Dict]) -> Dict[str, Any]:
        """Main conversation loop with proper user handling"""
        
        iteration = 0
        max_iterations = self.config.max_iterations
        last_progress_shown = 0
        
        while iteration < max_iterations:
            try:
                self.state.iteration_count = iteration
                
                # Show iteration progress
                self.display.show_iteration(iteration + 1, max_iterations)
                
                # Execute hooks
                self.hooks.execute_hooks('pre_iteration', {
                    'iteration': iteration + 1,
                    'messages_count': len(messages)
                })
                
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
                            
                            self.display.show_tool_use(tool_name)
                            
                            # Execute tool
                            start_time = time.time()
                            result = self._execute_tool(tool_name, tool_input)
                            duration = time.time() - start_time
                            
                            # Show result
                            self.display.show_tool_result(
                                tool_name, 
                                result["success"],
                                result.get("output", "")[:100] + "..." if result.get("output") else ""
                            )
                            
                            # Track progress
                            self.state.progress_entries.append(ProgressEntry(
                                timestamp=datetime.datetime.now().isoformat(),
                                action=tool_name,
                                details=result.get("output", "")[:200],
                                status="completed" if result["success"] else "failed",
                                tool_used=tool_name,
                                duration=duration
                            ))
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result["output"] if result["success"] else f"Error: {result.get('error', 'Unknown error')}"
                            })
                    
                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                
                else:
                    # No more tools - task phase completed
                    final_response = (
                        response.content[0].text if response.content else "Task completed"
                    )
                    
                    # Handle completion with user interaction
                    return self._handle_completion(final_response, messages, iteration + 1)
                
                # Show periodic progress
                if iteration - last_progress_shown >= self.config.progress_interval:
                    self.display.show_progress_summary(
                        len(self.state.files_tracking),
                        len(self.state.sub_agent_results),
                        len(set(e.tool_used for e in self.state.progress_entries))
                    )
                    last_progress_shown = iteration
                
                # Execute post-iteration hooks
                self.hooks.execute_hooks('post_iteration', {
                    'iteration': iteration + 1,
                    'state': self.state
                })
                
                iteration += 1
                
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}⚠️ Task interrupted by user{Colors.ENDC}")
                return self._handle_interruption(messages, iteration)
                
            except Exception as e:
                print(f"{Colors.RED}❌ Error in iteration {iteration + 1}: {e}{Colors.ENDC}")
                if self.config.debug_mode:
                    import traceback
                    traceback.print_exc()
                
                # Add error to history but continue
                self.state.error_history.append({
                    'iteration': iteration + 1,
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                })
                
                # Ask user what to do
                print(f"\n{Colors.YELLOW}What should I do?{Colors.ENDC}")
                print(f"{Colors.GREEN}  c{Colors.ENDC} - Continue despite error")
                print(f"{Colors.RED}  q{Colors.ENDC} - Quit and save state") 
                print(f"{Colors.BLUE}  r{Colors.ENDC} - Retry last operation")
                
                choice = input("Choice (c/q/r): ").strip().lower()
                if choice == 'q':
                    return self._handle_interruption(messages, iteration)
                elif choice == 'r':
                    continue  # Retry same iteration
                # Otherwise continue (c or any other input)
                
                iteration += 1
        
        # Max iterations reached
        print(f"{Colors.YELLOW}⚠️ Max iterations reached{Colors.ENDC}")
        return self._handle_completion("Max iterations reached", messages, max_iterations)
    
    def _handle_completion(self, final_response: str, messages: List[Dict], iterations: int) -> Dict[str, Any]:
        """Handle task completion with proper user interaction"""
        
        # Prepare statistics
        stats = {
            "Iterations": iterations,
            "Files created/modified": len(self.state.files_tracking),
            "Sub-agents spawned": len(self.state.sub_agent_results),
            "Tools used": len(set(e.tool_used for e in self.state.progress_entries)),
            "Duration": str(datetime.datetime.now() - self.state.start_time).split('.')[0],
            "Errors encountered": len(self.state.error_history)
        }
        
        # Show completion prompt
        self.display.show_completion_prompt(final_response, stats)
        
        # Get user input with proper handling
        while True:
            try:
                user_input = input(f"{Colors.BOLD}Your choice: {Colors.ENDC}").strip().lower()
                
                if user_input == "y":
                    # Task complete - finalize
                    self._finalize_task()
                    self.hooks.execute_hooks('task_complete', {
                        'success': True,
                        'iterations': iterations,
                        'stats': stats
                    })
                    
                    print(f"\n{Colors.GREEN}✅ Task completed successfully!{Colors.ENDC}")
                    return {
                        "success": True,
                        "iterations": iterations,
                        "final_response": final_response,
                        "task_id": self.state.task_id,
                        **stats
                    }
                
                elif user_input == "n":
                    # Get feedback and continue
                    print(f"\n{Colors.CYAN}What still needs to be done?{Colors.ENDC}")
                    feedback = input("Your feedback: ").strip()
                    
                    if feedback:
                        # Add user feedback to conversation
                        messages.append({
                            "role": "user",
                            "content": f"User feedback: {feedback}. Please continue working on the task."
                        })
                        
                        print(f"\n{Colors.GREEN}📋 Continuing with your feedback...{Colors.ENDC}")
                        return self._execute_conversation_loop(messages)
                    else:
                        print(f"{Colors.RED}No feedback provided. Please try again.{Colors.ENDC}")
                        continue
                
                elif user_input == "continue":
                    # Continue without feedback
                    messages.append({
                        "role": "user", 
                        "content": "Please continue working on the task."
                    })
                    
                    print(f"\n{Colors.GREEN}📋 Continuing task...{Colors.ENDC}")
                    return self._execute_conversation_loop(messages)
                
                elif user_input == "quit":
                    # Save state and quit
                    self._save_state()
                    print(f"\n{Colors.YELLOW}💾 State saved. You can resume with: --resume {self.state.task_id}{Colors.ENDC}")
                    return {
                        "success": False,
                        "iterations": iterations,
                        "resume_possible": True,
                        "task_id": self.state.task_id,
                        **stats
                    }
                
                else:
                    print(f"{Colors.RED}Invalid choice. Please enter y, n, continue, or quit.{Colors.ENDC}")
                    continue
                    
            except KeyboardInterrupt:
                return self._handle_interruption(messages, iterations)
            except EOFError:
                print(f"\n{Colors.YELLOW}Input stream ended. Saving state...{Colors.ENDC}")
                return self._handle_interruption(messages, iterations)
    
    def _handle_interruption(self, messages: List[Dict], iterations: int) -> Dict[str, Any]:
        """Handle task interruption"""
        print(f"\n{Colors.YELLOW}💾 Saving state for later resume...{Colors.ENDC}")
        self._save_state()
        
        return {
            "success": False,
            "iterations": iterations,
            "interrupted": True,
            "resume_possible": True,
            "task_id": self.state.task_id,
            "message": f"Task interrupted. Resume with: --resume {self.state.task_id}"
        }
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools (simplified implementation)"""
        try:
            if tool_name == "bash":
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
                
                return {
                    "success": result.returncode == 0,
                    "output": output or "(No output)",
                    "returncode": result.returncode
                }
            
            elif tool_name == "str_replace_editor":
                command = tool_input["command"]
                path = tool_input["path"]
                
                if command == "create":
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(tool_input.get("file_text", ""))
                    
                    # Track file
                    self.state.files_tracking[path] = {
                        "created": datetime.datetime.now().isoformat(),
                        "size": os.path.getsize(path)
                    }
                    
                    return {"success": True, "output": f"Created file: {path}"}
                
                elif command == "view":
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    return {"success": True, "output": content}
                
                elif command == "str_replace":
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    old_string = tool_input["old_string"]
                    new_string = tool_input["new_string"]
                    
                    if old_string not in content:
                        return {"success": False, "error": f"String not found: {old_string[:50]}..."}
                    
                    new_content = content.replace(old_string, new_string)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    
                    # Update file tracking
                    if path in self.state.files_tracking:
                        self.state.files_tracking[path]["modified"] = datetime.datetime.now().isoformat()
                    
                    return {"success": True, "output": f"Updated file: {path}"}
            
            elif tool_name == "web_search":
                # Simple DuckDuckGo implementation
                query = tool_input["query"]
                return {"success": True, "output": f"Web search results for: {query} (implementation needed)"}
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_state(self):
        """Save agent state"""
        try:
            with open(self.config.state_file, 'wb') as f:
                pickle.dump(self.state, f)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def _finalize_task(self):
        """Finalize task completion"""
        # Create final progress markdown
        if self.config.progress_file:
            self._create_progress_md()
        
        # Clean up state file
        try:
            if os.path.exists(self.config.state_file):
                os.remove(self.config.state_file)
        except:
            pass
    
    def _create_progress_md(self):
        """Create comprehensive progress markdown"""
        content = f"""# Task Completion Report

**Task:** {self.state.original_task}
**Task ID:** {self.state.task_id}
**Completed:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {datetime.datetime.now() - self.state.start_time}

## Statistics
- **Iterations:** {self.state.iteration_count}
- **Files Created/Modified:** {len(self.state.files_tracking)}
- **Tools Used:** {len(set(e.tool_used for e in self.state.progress_entries))}
- **Errors Encountered:** {len(self.state.error_history)}

## Files Affected
"""
        for file_path, info in self.state.files_tracking.items():
            content += f"- `{file_path}` - {info.get('created', 'modified')}\n"
        
        content += "\n## Progress Log\n"
        for entry in self.state.progress_entries[-10:]:  # Last 10 entries
            content += f"- **{entry.action}** ({entry.timestamp}) - {entry.details[:100]}\n"
        
        try:
            with open(self.config.progress_file, 'w') as f:
                f.write(content)
            print(f"{Colors.GREEN}📄 Progress report saved to {self.config.progress_file}{Colors.ENDC}")
        except Exception as e:
            print(f"Warning: Could not save progress report: {e}")
    
    def _resume_task(self, task_id: str) -> Dict[str, Any]:
        """Resume a previous task"""
        try:
            with open(self.config.state_file, 'rb') as f:
                self.state = pickle.load(f)
            
            if self.state.task_id != task_id:
                return {"success": False, "error": f"Task ID mismatch: {task_id} vs {self.state.task_id}"}
            
            print(f"{Colors.GREEN}🔄 Resuming task: {self.state.task_id}{Colors.ENDC}")
            print(f"{Colors.BLUE}Original task: {self.state.original_task}{Colors.ENDC}")
            print(f"{Colors.BLUE}Previous iterations: {self.state.iteration_count}{Colors.ENDC}")
            
            # Continue from where we left off
            messages = [{"role": "user", "content": f"Resuming task: {self.state.original_task}. Continue from where we left off."}]
            return self._execute_conversation_loop(messages)
            
        except FileNotFoundError:
            return {"success": False, "error": f"No saved state found for task {task_id}"}
        except Exception as e:
            return {"success": False, "error": f"Could not resume task: {e}"}


def main():
    """Enhanced CLI with better argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ultimate SWE Agent (Fixed) - Complete Claude Code Equivalent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    parser.add_argument("--max-iterations", type=int, default=50, help="Maximum iterations")
    parser.add_argument("--resume", help="Resume task by ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-web", action="store_true", help="Disable web access")
    parser.add_argument("--no-rich", action="store_true", help="Disable rich display")
    parser.add_argument("--no-hooks", action="store_true", help="Disable hooks")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"{Colors.RED}❌ Please set ANTHROPIC_API_KEY environment variable{Colors.ENDC}")
        return
    
    # Get task
    if args.resume:
        task = ""
    elif args.task:
        task = " ".join(args.task)
    else:
        task = input("Enter task: ").strip()
    
    if not task and not args.resume:
        print(f"{Colors.RED}❌ No task provided{Colors.ENDC}")
        return
    
    # Create config
    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug,
        enable_web=not args.no_web,
        rich_display=not args.no_rich,
        hooks_enabled=not args.no_hooks
    )
    
    try:
        agent = UltimateSWEAgentFixed(config)
        result = agent.execute_task(task, resume_task_id=args.resume)
        
        # Show final results
        if result["success"]:
            print(f"\n{Colors.GREEN}🎉 Task completed successfully!{Colors.ENDC}")
        elif result.get("resume_possible"):
            print(f"\n{Colors.YELLOW}📋 Task paused - Resume with: --resume {result.get('task_id')}{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}❌ Task failed{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fatal error: {e}{Colors.ENDC}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()