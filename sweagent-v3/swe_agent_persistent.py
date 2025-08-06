"""
SWE Agent V3 Persistent - Claude Code Error Recovery
Implements smart error recovery with context persistence like Claude Code
"""

import os
import json
import pickle
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from anthropic import Anthropic


@dataclass
class PersistentState:
    """Persistent state to maintain context across errors"""
    task_id: str
    original_task: str
    completed_steps: List[str]
    current_step: str
    error_history: List[Dict]
    iteration_count: int
    last_successful_operation: str
    working_context: Dict[str, Any]


@dataclass
class Config:
    """Enhanced configuration with persistence"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 30
    debug_mode: bool = False
    state_file: str = ".swe_agent_state.pkl"
    context_retention: int = 10  # Keep last N conversation turns


def create_persistent_tool_schema():
    """Enhanced tools with recovery awareness"""
    return [
        {
            "name": "bash",
            "description": "Execute bash commands with error recovery awareness",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                    "timeout": {"type": "number", "description": "Command timeout in seconds", "default": 30}
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
                        "description": "The command to execute",
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {"type": "string", "description": "Content for create command"},
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                },
                "required": ["command", "path"],
            },
        },
        {
            "name": "ask_user_step",
            "description": "Ask user for guidance on specific step completion or error recovery",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_description": {"type": "string", "description": "What step was attempted"},
                    "status": {
                        "type": "string", 
                        "enum": ["completed", "failed", "needs_guidance"],
                        "description": "Status of the step"
                    },
                    "error_details": {"type": "string", "description": "Error details if step failed"},
                    "suggested_next_action": {"type": "string", "description": "Suggested recovery action"},
                },
                "required": ["step_description", "status"],
            },
        },
        {
            "name": "save_progress",
            "description": "Save current progress and context for recovery",
            "input_schema": {
                "type": "object",
                "properties": {
                    "completed_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of completed steps"
                    },
                    "current_context": {"type": "string", "description": "Current working context"},
                },
                "required": ["completed_steps"],
            },
        },
        {
            "name": "load_progress",
            "description": "Load previous progress to continue from failure point",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "task_id": {"type": "string", "description": "Task identifier to load"}
                },
                "required": ["task_id"],
            },
        },
    ]


class PersistentSWEAgent:
    """SWE Agent with Claude Code-like error recovery and persistence"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_persistent_tool_schema()
        self.state: Optional[PersistentState] = None
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
            
        self.state_path = Path(config.working_dir) / config.state_file
        
        print(f"🚀 Persistent SWE Agent - Claude Code Error Recovery")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"💾 State file: {self.state_path}")
        print(f"🔧 Enhanced recovery tools available")

    def execute_task(self, task: str, resume_task_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute task with smart error recovery"""
        
        # Try to resume existing task or start new one
        if resume_task_id:
            if self._load_state(resume_task_id):
                print(f"📂 Resuming task: {self.state.original_task}")
                print(f"✅ Completed steps: {len(self.state.completed_steps)}")
                print(f"🔄 Current step: {self.state.current_step}")
                task = self.state.original_task
            else:
                print(f"⚠️ Could not resume task {resume_task_id}, starting new task")
                
        if not self.state:
            # Create new task state
            import hashlib
            task_id = hashlib.md5(task.encode()).hexdigest()[:8]
            self.state = PersistentState(
                task_id=task_id,
                original_task=task,
                completed_steps=[],
                current_step="Starting task analysis",
                error_history=[],
                iteration_count=0,
                last_successful_operation="",
                working_context={}
            )
            
        print(f"\n📋 Task ID: {self.state.task_id}")
        print(f"📋 Task: {task}")

        # Build system prompt with recovery context
        system_prompt = self._build_recovery_aware_prompt()
        
        # Initialize or resume conversation
        if hasattr(self.state, 'conversation_history') and self.state.conversation_history:
            messages = self.state.conversation_history[-self.config.context_retention:]
        else:
            messages = [{"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}]
            self.state.working_context['conversation_history'] = messages

        max_iterations = self.config.max_iterations
        
        while self.state.iteration_count < max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {self.state.iteration_count + 1}")
                    print(f"🎯 Current step: {self.state.current_step}")

                # Get response
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages,
                    tools=self.tools,
                )

                # Add response to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Handle tool use
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            print(f"⏺ {tool_name}()")
                            
                            # Execute with recovery awareness
                            result = self._execute_persistent_tool(tool_name, tool_input)
                            
                            # Handle user interaction for errors/guidance
                            if (tool_name == "ask_user_step" and result["success"] 
                                and tool_input.get("status") in ["failed", "needs_guidance"]):
                                user_guidance = self._get_user_guidance(tool_input, result)
                                result["output"] = user_guidance
                                
                                # Update state based on user guidance
                                self._process_user_guidance(user_guidance, tool_input)
                            
                            # Display result like Claude Code
                            print(f"  ⎿ {self._format_tool_result(tool_name, result)}")
                            
                            # Save progress after successful operations
                            if result["success"] and tool_name != "ask_user_step":
                                self._update_progress(tool_name, tool_input, result)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result["output"] if result["success"] 
                                         else f"Error: {result.get('error', 'Unknown error')}"
                            })

                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                    
                    # Save conversation state
                    self.state.working_context['conversation_history'] = messages
                    
                else:
                    # Task might be complete
                    final_response = (
                        response.content[0].text if response.content else "Task completed"
                    )
                    
                    print(f"💭 {final_response}")
                    
                    # Ask user for final confirmation
                    print("\n❓ Is the overall task complete? (y/n/continue)")
                    user_input = input("Response: ").strip().lower()
                    
                    if user_input == "y":
                        self._cleanup_state()
                        return {
                            "success": True,
                            "iterations": self.state.iteration_count + 1,
                            "final_response": final_response,
                            "task_id": self.state.task_id
                        }
                    elif user_input == "n":
                        feedback = input("What still needs to be done? ")
                        messages.append({
                            "role": "user", 
                            "content": f"Task not complete. User feedback: {feedback}"
                        })
                    else:
                        messages.append({
                            "role": "user",
                            "content": "Please continue working on the task."
                        })

                self.state.iteration_count += 1
                self._save_state()

            except Exception as e:
                print(f"❌ Error in iteration {self.state.iteration_count + 1}: {e}")
                
                # Record error in history
                error_record = {
                    "iteration": self.state.iteration_count + 1,
                    "error": str(e),
                    "step": self.state.current_step,
                    "timestamp": str(os.path.getmtime)
                }
                self.state.error_history.append(error_record)
                
                # Ask user for error recovery guidance
                print(f"🆘 Error occurred during: {self.state.current_step}")
                print(f"Error details: {str(e)}")
                print("\n❓ How should we proceed?")
                print("1. retry - Try the same step again")
                print("2. skip - Skip this step and continue")
                print("3. abort - Stop the task")
                print("4. debug - Get more error details")
                
                choice = input("Choice (1-4): ").strip()
                
                if choice == "1":
                    print("🔄 Retrying current step...")
                    messages.append({
                        "role": "user",
                        "content": f"Error occurred: {e}. Please retry the current step with a different approach."
                    })
                elif choice == "2":
                    print("⏭️ Skipping current step...")
                    self.state.completed_steps.append(f"SKIPPED: {self.state.current_step}")
                    messages.append({
                        "role": "user",
                        "content": f"Error occurred: {e}. User chose to skip this step. Please continue with the next step."
                    })
                elif choice == "3":
                    self._save_state()
                    return {
                        "success": False,
                        "iterations": self.state.iteration_count + 1,
                        "error": str(e),
                        "task_id": self.state.task_id,
                        "resume_possible": True
                    }
                elif choice == "4":
                    if self.config.debug_mode:
                        import traceback
                        traceback.print_exc()
                    messages.append({
                        "role": "user",
                        "content": f"Error details: {str(e)}. Please analyze this error and suggest a solution."
                    })
                
                self.state.iteration_count += 1
                self._save_state()

        # Max iterations reached
        print("⚠️ Max iterations reached, saving state for resume")
        self._save_state()
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max iterations reached",
            "task_id": self.state.task_id,
            "resume_possible": True
        }

    def _build_recovery_aware_prompt(self) -> str:
        """Build system prompt with recovery context"""
        
        base_prompt = """You are a persistent software engineering assistant that works like Claude Code with smart error recovery.

RECOVERY BEHAVIOR:
- When errors occur, you continue from the failure point instead of restarting
- Use ask_user_step to get guidance on failures or unclear situations  
- Save progress frequently with save_progress tool
- Build on previous work rather than recreating from scratch

AVAILABLE TOOLS:
- bash: Execute shell commands (with timeout and error handling)
- str_replace_editor: Create, read, edit files
- ask_user_step: Get user guidance on step completion or failures
- save_progress: Save current progress for recovery
- load_progress: Resume from previous state

WORKFLOW:
1. Break complex tasks into clear steps
2. Execute one step at a time
3. On success: save progress and continue
4. On failure: use ask_user_step for guidance, then continue with user input
5. Never restart completed work - always build incrementally"""

        # Add context from previous work if resuming
        if self.state and self.state.completed_steps:
            context = f"""

PREVIOUS PROGRESS:
✅ Completed steps: {self.state.completed_steps}
🎯 Current focus: {self.state.current_step}
🕐 Last success: {self.state.last_successful_operation}

Continue from where we left off, building on this previous work."""
            base_prompt += context

        return base_prompt + f"\n\nWorking directory: {os.getcwd()}"

    def _execute_persistent_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools with persistence awareness"""
        
        try:
            if tool_name == "bash":
                return self._execute_bash(tool_input["command"], tool_input.get("timeout", 30))
            elif tool_name == "str_replace_editor":
                return self._execute_str_replace_editor(tool_input)
            elif tool_name == "ask_user_step":
                return {"success": True, "output": "User guidance requested"}
            elif tool_name == "save_progress":
                return self._save_progress_tool(tool_input)
            elif tool_name == "load_progress":
                return self._load_progress_tool(tool_input)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_bash(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute bash with smart timeout detection"""
        import subprocess
        
        # Smart timeout based on command type
        if any(cmd in command.lower() for cmd in ["install", "pip", "npm", "apt", "yum"]):
            timeout = min(180, timeout * 6)  # 3 minutes for installs
        elif any(cmd in command.lower() for cmd in ["git clone", "wget", "curl"]):
            timeout = min(120, timeout * 4)  # 2 minutes for downloads
            
        try:
            print(f"  🔧 Running: {command}")
            if timeout > 30:
                print(f"  ⏱️ Extended timeout: {timeout}s")
                
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

            success = result.returncode == 0
            if success:
                self.state.last_successful_operation = f"bash: {command[:50]}..."

            return {
                "success": success,
                "output": output or "(No output)",
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_str_replace_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """File operations with persistence"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                content = tool_input.get("file_text", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.state.last_successful_operation = f"Created: {path}"
                return {"success": True, "output": f"Created file: {path}"}

            elif command == "view":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
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
                    
                self.state.last_successful_operation = f"Edited: {path}"
                return {"success": True, "output": f"Updated {path}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_progress_tool(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Save progress tool implementation"""
        try:
            completed_steps = tool_input["completed_steps"]
            self.state.completed_steps = completed_steps
            self.state.working_context["manual_save"] = tool_input.get("current_context", "")
            self._save_state()
            return {"success": True, "output": f"Progress saved: {len(completed_steps)} steps completed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_progress_tool(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Load progress tool implementation"""
        try:
            task_id = tool_input["task_id"]
            if self._load_state(task_id):
                return {
                    "success": True, 
                    "output": f"Loaded task {task_id}: {len(self.state.completed_steps)} completed steps"
                }
            else:
                return {"success": False, "error": f"Could not load task {task_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_user_guidance(self, tool_input: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Get user guidance for error recovery"""
        step_description = tool_input["step_description"]
        status = tool_input["status"]
        error_details = tool_input.get("error_details", "")
        suggested_action = tool_input.get("suggested_next_action", "")

        print(f"\n📋 Step: {step_description}")
        print(f"📊 Status: {status.upper()}")
        
        if error_details:
            print(f"❌ Error: {error_details}")
        if suggested_action:
            print(f"💡 Suggested: {suggested_action}")

        if status == "failed":
            print("\n❓ How should we handle this failure?")
            print("1. retry - Try again with same approach")  
            print("2. alternative - Try a different approach")
            print("3. skip - Skip this step")
            print("4. manual - I'll handle this manually")
        else:
            print("\n❓ How should we proceed?")
            print("1. continue - Proceed to next step")
            print("2. modify - Modify this step")
            print("3. pause - Pause here")

        choice = input("Your choice: ").strip()
        additional_info = ""
        
        if choice in ["2", "alternative", "modify"]:
            additional_info = input("What approach should we try? ")
        elif choice in ["4", "manual"]:
            additional_info = input("What did you do manually? ")
            
        return f"User chose '{choice}'. Additional info: {additional_info}"

    def _process_user_guidance(self, guidance: str, tool_input: Dict[str, Any]):
        """Process user guidance and update state"""
        if "skip" in guidance.lower():
            self.state.completed_steps.append(f"SKIPPED: {tool_input['step_description']}")
        elif "manual" in guidance.lower():
            self.state.completed_steps.append(f"MANUAL: {tool_input['step_description']}")
        # Other guidance is handled by continuing the conversation

    def _update_progress(self, tool_name: str, tool_input: Dict, result: Dict):
        """Update progress after successful operations"""
        if tool_name == "bash":
            operation = f"Executed: {tool_input['command'][:50]}..."
        elif tool_name == "str_replace_editor":
            operation = f"File {tool_input['command']}: {tool_input['path']}"
        else:
            operation = f"Used tool: {tool_name}"
            
        if operation not in self.state.completed_steps:
            self.state.completed_steps.append(operation)

    def _save_state(self):
        """Save current state to disk"""
        try:
            with open(self.state_path, 'wb') as f:
                pickle.dump(self.state, f)
            if self.config.debug_mode:
                print(f"💾 State saved: {self.state_path}")
        except Exception as e:
            print(f"⚠️ Could not save state: {e}")

    def _load_state(self, task_id: str) -> bool:
        """Load state from disk"""
        try:
            if not self.state_path.exists():
                return False
                
            with open(self.state_path, 'rb') as f:
                loaded_state = pickle.load(f)
                
            if loaded_state.task_id == task_id:
                self.state = loaded_state
                return True
            return False
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")
            return False

    def _cleanup_state(self):
        """Clean up state file after successful completion"""
        try:
            if self.state_path.exists():
                self.state_path.unlink()
                print(f"🧹 Cleaned up state file")
        except Exception:
            pass

    def _format_tool_result(self, tool_name: str, result: Dict) -> str:
        """Format tool results like Claude Code"""
        if result["success"]:
            if tool_name == "bash" and result.get("output"):
                return f"✅ Command completed"
            elif tool_name == "str_replace_editor":
                return f"✅ File operation completed"
            else:
                return f"✅ {tool_name} completed"
        else:
            return f"❌ {tool_name} failed: {result.get('error', 'Unknown error')}"


def main():
    """CLI entry point with resume capability"""
    import argparse

    parser = argparse.ArgumentParser(description="Persistent SWE Agent - Claude Code Recovery")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")  
    parser.add_argument("--max-iterations", type=int, default=30, help="Maximum iterations")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--resume", help="Resume task by ID")

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return

    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug,
    )

    try:
        agent = PersistentSWEAgent(config)
        
        if args.resume:
            result = agent.execute_task("", resume_task_id=args.resume)
        else:
            # Get task
            if args.task:
                task = " ".join(args.task)
            else:
                task = input("Enter task: ").strip()

            if not task:
                print("❌ No task provided")
                return

            result = agent.execute_task(task)

        print(f"\n📊 Final Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")
        print(f"🆔 Task ID: {result['task_id']}")

        if not result["success"]:
            if result.get("resume_possible"):
                print(f"💾 Task can be resumed with: --resume {result['task_id']}")
            if "error" in result:
                print(f"❌ Error: {result['error']}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user - state saved for resume")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()