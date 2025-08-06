"""
SWE Agent V3 Enhanced - Claude Code with Intelligent Summarization
Implements Claude Code's context management, progress tracking, and summarization patterns
"""

import os
import json
import pickle
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from anthropic import Anthropic


@dataclass
class ProgressEntry:
    """Individual progress entry for tracking"""
    timestamp: str
    action: str
    details: str
    files_affected: List[str] = field(default_factory=list)
    status: str = "completed"  # completed, failed, skipped


@dataclass
class ConversationSummary:
    """Summary of conversation context"""
    summary_id: str
    iterations_covered: tuple  # (start, end)
    key_accomplishments: List[str]
    current_focus: str
    next_steps: List[str]
    files_created_modified: List[str]
    errors_resolved: List[str]
    timestamp: str


@dataclass
class EnhancedPersistentState:
    """Enhanced state with summarization support"""
    task_id: str
    original_task: str
    completed_steps: List[str]
    current_step: str
    error_history: List[Dict]
    iteration_count: int
    last_successful_operation: str
    working_context: Dict[str, Any]
    progress_entries: List[ProgressEntry] = field(default_factory=list)
    conversation_summaries: List[ConversationSummary] = field(default_factory=list)
    files_tracking: Dict[str, Dict] = field(default_factory=dict)  # file -> {created, modified, size}


@dataclass
class Config:
    """Enhanced configuration with summarization"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 30
    debug_mode: bool = False
    state_file: str = ".swe_agent_state.pkl"
    progress_file: str = "progress.md"
    context_retention: int = 8  # Conversation turns to keep
    summarization_threshold: int = 12  # Summarize after N iterations
    progress_tracking: bool = True


def create_enhanced_tool_schema():
    """Tools with summarization and progress tracking"""
    return [
        {
            "name": "bash",
            "description": "Execute bash commands with progress tracking",
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
            "description": "Create, read, and edit files with automatic tracking",
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
            "name": "create_summary",
            "description": "Create intelligent summary of recent progress like Claude Code",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why creating summary (context_length, checkpoint, etc.)"},
                    "key_accomplishments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Major things accomplished recently"
                    },
                    "current_focus": {"type": "string", "description": "What we're currently working on"},
                    "next_steps": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Planned next steps"
                    }
                },
                "required": ["reason", "key_accomplishments", "current_focus"],
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
            "name": "update_progress_md",
            "description": "Update progress.md with timestamped file tracking",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "What action was just completed"},
                    "files_modified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files that were created or modified"
                    }
                },
                "required": ["action"],
            },
        },
    ]


class EnhancedSummarizationAgent:
    """SWE Agent with Claude Code summarization and progress tracking"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_enhanced_tool_schema()
        self.state: Optional[EnhancedPersistentState] = None
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
            
        self.state_path = Path(config.working_dir) / config.state_file
        self.progress_path = Path(config.working_dir) / config.progress_file
        
        print(f"🚀 Enhanced SWE Agent - Claude Code with Intelligent Summarization")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📊 Progress tracking: {'ON' if config.progress_tracking else 'OFF'}")
        print(f"🧠 Auto-summarization: Every {config.summarization_threshold} iterations")
        print(f"💾 Progress file: {self.progress_path}")

    def execute_task(self, task: str, resume_task_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute task with intelligent summarization like Claude Code"""
        
        # Try to resume or start new
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
            self.state = EnhancedPersistentState(
                task_id=task_id,
                original_task=task,
                completed_steps=[],
                current_step="Starting task analysis",
                error_history=[],
                iteration_count=0,
                last_successful_operation="",
                working_context={}
            )
            
            # Initialize progress.md
            if self.config.progress_tracking:
                self._initialize_progress_md()
                
        print(f"\n📋 Task ID: {self.state.task_id}")
        print(f"📋 Task: {task}")

        # Build system prompt with summarization awareness
        system_prompt = self._build_summarization_aware_prompt()
        
        # Initialize or resume conversation with summaries
        messages = self._initialize_conversation(system_prompt, task)

        max_iterations = self.config.max_iterations
        
        while self.state.iteration_count < max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {self.state.iteration_count + 1}")
                    print(f"🎯 Current step: {self.state.current_step}")

                # Check if summarization is needed (like Claude Code does)
                if (self.state.iteration_count > 0 and 
                    self.state.iteration_count % self.config.summarization_threshold == 0):
                    print(f"🧠 Creating summary after {self.state.iteration_count} iterations...")
                    self._create_intelligent_summary(messages)
                    messages = self._compress_conversation_with_summary(messages)

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
                            
                            # Execute with progress tracking
                            result = self._execute_enhanced_tool(tool_name, tool_input)
                            
                            # Handle user interaction
                            if (tool_name == "ask_user_step" and result["success"] 
                                and tool_input.get("status") in ["failed", "needs_guidance"]):
                                user_guidance = self._get_user_guidance(tool_input, result)
                                result["output"] = user_guidance
                                self._process_user_guidance(user_guidance, tool_input)
                            
                            # Display result like Claude Code
                            print(f"  ⎿ {self._format_tool_result(tool_name, result)}")
                            
                            # Track progress
                            if result["success"]:
                                self._track_progress(tool_name, tool_input, result)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result["output"] if result["success"] 
                                         else f"Error: {result.get('error', 'Unknown error')}"
                            })

                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                    
                else:
                    # Task might be complete
                    final_response = (
                        response.content[0].text if response.content else "Task completed"
                    )
                    
                    print(f"💭 {final_response}")
                    
                    # Create final summary
                    self._create_completion_summary()
                    
                    # Ask user for final confirmation
                    print("\n❓ Is the overall task complete? (y/n/continue)")
                    user_input = input("Response: ").strip().lower()
                    
                    if user_input == "y":
                        self._finalize_progress_md()
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
                
                # Record error with context
                error_record = {
                    "iteration": self.state.iteration_count + 1,
                    "error": str(e),
                    "step": self.state.current_step,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "context": self._get_current_context_summary()
                }
                self.state.error_history.append(error_record)
                
                # Handle error recovery with summarized context
                recovery_action = self._handle_error_with_context(e, messages)
                
                if recovery_action == "abort":
                    self._save_state()
                    return {
                        "success": False,
                        "iterations": self.state.iteration_count + 1,
                        "error": str(e),
                        "task_id": self.state.task_id,
                        "resume_possible": True
                    }
                elif recovery_action == "retry":
                    messages.append({
                        "role": "user",
                        "content": f"Error occurred: {e}. Please retry with a different approach based on our progress so far."
                    })
                
                self.state.iteration_count += 1
                self._save_state()

        # Max iterations reached - create final summary
        print("⚠️ Max iterations reached, creating final summary...")
        self._create_completion_summary()
        self._save_state()
        
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max iterations reached",
            "task_id": self.state.task_id,
            "resume_possible": True
        }

    def _build_summarization_aware_prompt(self) -> str:
        """Build system prompt with summarization context"""
        
        base_prompt = """You are an intelligent software engineering assistant that works like Claude Code with advanced summarization.

SUMMARIZATION BEHAVIOR:
- After significant progress, use create_summary to capture key accomplishments
- Compress context while preserving essential information
- Track file changes and progress systematically
- Provide clear checkpoints for complex tasks

PROGRESS TRACKING:
- Use update_progress_md to maintain timestamped progress log
- Track all file creations and modifications
- Document decision points and error resolutions

TOOLS AVAILABLE:
- bash: Execute commands with progress tracking
- str_replace_editor: File operations with automatic tracking
- create_summary: Intelligent context summarization
- ask_user_step: User guidance and confirmation
- update_progress_md: Progress documentation

WORKFLOW:
1. Work systematically on tasks
2. Track progress in real-time  
3. Summarize context when needed
4. Build on previous work intelligently
5. Document decisions and outcomes"""

        # Add context from summaries if resuming
        if self.state and self.state.conversation_summaries:
            latest_summary = self.state.conversation_summaries[-1]
            context = f"""

PREVIOUS PROGRESS SUMMARY:
📝 Key accomplishments: {latest_summary.key_accomplishments}
🎯 Current focus: {latest_summary.current_focus}
📁 Files created/modified: {latest_summary.files_created_modified}
🛠️ Errors resolved: {latest_summary.errors_resolved}
➡️ Next steps: {latest_summary.next_steps}

Build on this progress without repeating completed work."""
            base_prompt += context

        return base_prompt + f"\n\nWorking directory: {os.getcwd()}"

    def _initialize_conversation(self, system_prompt: str, task: str) -> List[Dict]:
        """Initialize conversation with summary context"""
        if self.state.conversation_summaries:
            # Start with summarized context
            summary_context = self._build_summary_context()
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{summary_context}\n\nContinue task: {task}"}]
        else:
            # Fresh start
            messages = [{"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}]
        
        return messages

    def _create_intelligent_summary(self, messages: List[Dict]):
        """Create intelligent summary like Claude Code does"""
        try:
            # Extract recent accomplishments and context
            recent_messages = messages[-10:]  # Last 10 messages for summary
            
            # Build summary prompt
            summary_prompt = """Analyze the recent conversation and create a concise summary focusing on:
1. Key accomplishments in the last several iterations
2. Current focus/what we're working on now
3. Files that were created or modified
4. Any errors that were resolved
5. Next logical steps

Be concise but capture essential progress context."""
            
            # Get summary from Claude
            summary_response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": summary_prompt},
                    {"role": "assistant", "content": str(recent_messages)}
                ]
            )
            
            summary_text = summary_response.content[0].text if summary_response.content else ""
            
            # Create structured summary
            summary_id = f"summary_{len(self.state.conversation_summaries) + 1}"
            conversation_summary = ConversationSummary(
                summary_id=summary_id,
                iterations_covered=(max(0, self.state.iteration_count - 10), self.state.iteration_count),
                key_accomplishments=self._extract_accomplishments(summary_text),
                current_focus=self._extract_current_focus(summary_text),
                next_steps=self._extract_next_steps(summary_text),
                files_created_modified=list(self.state.files_tracking.keys()),
                errors_resolved=[err.get('error', '')[:50] for err in self.state.error_history[-3:]],
                timestamp=datetime.datetime.now().isoformat()
            )
            
            self.state.conversation_summaries.append(conversation_summary)
            
            print(f"📋 Summary created: {len(conversation_summary.key_accomplishments)} key accomplishments")
            
        except Exception as e:
            print(f"⚠️ Could not create summary: {e}")

    def _execute_enhanced_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools with enhanced tracking"""
        
        try:
            if tool_name == "bash":
                return self._execute_bash(tool_input["command"], tool_input.get("timeout", 30))
            elif tool_name == "str_replace_editor":
                return self._execute_str_replace_editor(tool_input)
            elif tool_name == "create_summary":
                return self._execute_create_summary(tool_input)
            elif tool_name == "ask_user_step":
                return {"success": True, "output": "User guidance requested"}
            elif tool_name == "update_progress_md":
                return self._execute_update_progress_md(tool_input)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_summary(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create_summary tool"""
        try:
            reason = tool_input["reason"]
            key_accomplishments = tool_input["key_accomplishments"]
            current_focus = tool_input["current_focus"]
            next_steps = tool_input.get("next_steps", [])
            
            # Create manual summary
            summary_id = f"manual_{len(self.state.conversation_summaries) + 1}"
            conversation_summary = ConversationSummary(
                summary_id=summary_id,
                iterations_covered=(self.state.iteration_count - 5, self.state.iteration_count),
                key_accomplishments=key_accomplishments,
                current_focus=current_focus,
                next_steps=next_steps,
                files_created_modified=list(self.state.files_tracking.keys()),
                errors_resolved=[],
                timestamp=datetime.datetime.now().isoformat()
            )
            
            self.state.conversation_summaries.append(conversation_summary)
            
            return {
                "success": True,
                "output": f"Summary created - Reason: {reason}, Accomplishments: {len(key_accomplishments)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_update_progress_md(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Update progress.md with timestamped entries"""
        try:
            action = tool_input["action"]
            files_modified = tool_input.get("files_modified", [])
            
            # Track files
            for file_path in files_modified:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    self.state.files_tracking[file_path] = {
                        "last_modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size,
                        "action": action
                    }
            
            # Add progress entry
            progress_entry = ProgressEntry(
                timestamp=datetime.datetime.now().isoformat(),
                action=action,
                details=f"Modified {len(files_modified)} files" if files_modified else "Action completed",
                files_affected=files_modified,
                status="completed"
            )
            
            self.state.progress_entries.append(progress_entry)
            
            # Update progress.md
            self._update_progress_md_file()
            
            return {
                "success": True,
                "output": f"Progress updated: {action} - {len(files_modified)} files tracked"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_bash(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Enhanced bash with progress tracking"""
        import subprocess
        
        # Smart timeout
        if any(cmd in command.lower() for cmd in ["install", "pip", "npm", "apt"]):
            timeout = min(180, timeout * 6)
            
        try:
            print(f"  🔧 Running: {command}")
            if timeout > 30:
                print(f"  ⏱️ Extended timeout: {timeout}s")
                
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd()
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"

            success = result.returncode == 0
            if success:
                self.state.last_successful_operation = f"bash: {command[:50]}..."
                
                # Track any files that might have been created
                self._scan_for_new_files(command)

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
        """File operations with tracking"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                content = tool_input.get("file_text", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Track file creation
                self.state.files_tracking[path] = {
                    "created": datetime.datetime.now().isoformat(),
                    "size": len(content),
                    "action": "created"
                }
                
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
                
                # Track file modification
                self.state.files_tracking[path] = {
                    "modified": datetime.datetime.now().isoformat(),
                    "size": len(new_content),
                    "action": "modified"
                }
                    
                self.state.last_successful_operation = f"Edited: {path}"
                return {"success": True, "output": f"Updated {path}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _initialize_progress_md(self):
        """Initialize progress.md file"""
        content = f"""# Progress Report - {self.state.original_task}

**Task ID:** `{self.state.task_id}`  
**Started:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Status:** In Progress

## Task Description
{self.state.original_task}

## Progress Timeline

"""
        with open(self.progress_path, "w") as f:
            f.write(content)

    def _update_progress_md_file(self):
        """Update progress.md with latest entries"""
        if not self.config.progress_tracking:
            return
            
        try:
            # Read current content
            if self.progress_path.exists():
                with open(self.progress_path, "r") as f:
                    current_content = f.read()
            else:
                current_content = ""
            
            # Build updated content
            content = f"""# Progress Report - {self.state.original_task}

**Task ID:** `{self.state.task_id}`  
**Started:** {self.state.progress_entries[0].timestamp if self.state.progress_entries else 'Unknown'}  
**Last Updated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Status:** {'Completed' if len(self.state.completed_steps) > 5 else 'In Progress'}  
**Iterations:** {self.state.iteration_count}

## Task Description
{self.state.original_task}

## Key Accomplishments
"""
            
            # Add summaries
            for summary in self.state.conversation_summaries:
                content += f"\n### {summary.summary_id} ({summary.timestamp[:19]})\n"
                for acc in summary.key_accomplishments:
                    content += f"- {acc}\n"
                content += f"\n**Current Focus:** {summary.current_focus}\n"
            
            content += "\n## Files Created/Modified\n\n"
            for file_path, info in self.state.files_tracking.items():
                action = info.get('action', 'unknown')
                timestamp = info.get('created') or info.get('modified', 'unknown')
                size = info.get('size', 0)
                content += f"- **{file_path}** - {action} ({timestamp[:19]}, {size} bytes)\n"
            
            content += "\n## Detailed Timeline\n\n"
            for entry in self.state.progress_entries:
                status_emoji = {"completed": "✅", "failed": "❌", "skipped": "⏭️"}.get(entry.status, "🔄")
                content += f"### {entry.timestamp[:19]} {status_emoji}\n"
                content += f"**Action:** {entry.action}\n"
                content += f"**Details:** {entry.details}\n"
                if entry.files_affected:
                    content += f"**Files:** {', '.join(entry.files_affected)}\n"
                content += "\n"
            
            # Add error history
            if self.state.error_history:
                content += "## Error History\n\n"
                for error in self.state.error_history:
                    content += f"- **{error['timestamp'][:19]}** - {error['step']}: {error['error'][:100]}...\n"
            
            with open(self.progress_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            print(f"⚠️ Could not update progress.md: {e}")

    def _scan_for_new_files(self, command: str):
        """Scan for new files created by bash commands"""
        # Simple heuristic - look for file creation patterns
        if any(pattern in command.lower() for pattern in ["touch", "echo >", "cat >", "mkdir"]):
            try:
                # Find recently created files
                for path in Path(".").rglob("*"):
                    if path.is_file():
                        stat = path.stat()
                        age = datetime.datetime.now().timestamp() - stat.st_mtime
                        if age < 10:  # Created in last 10 seconds
                            file_str = str(path)
                            if file_str not in self.state.files_tracking:
                                self.state.files_tracking[file_str] = {
                                    "created": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "size": stat.st_size,
                                    "action": "created_by_command"
                                }
            except Exception:
                pass  # Ignore scan errors

    # Additional helper methods for summarization
    def _extract_accomplishments(self, summary_text: str) -> List[str]:
        """Extract key accomplishments from summary text"""
        # Simple extraction - look for bullet points or numbered lists
        lines = summary_text.split('\n')
        accomplishments = []
        for line in lines:
            if line.strip().startswith(('-', '*', '•')) or any(line.strip().startswith(f"{i}.") for i in range(1, 10)):
                accomplishments.append(line.strip().lstrip('-*•0123456789. '))
        return accomplishments[:5]  # Limit to 5 key items

    def _extract_current_focus(self, summary_text: str) -> str:
        """Extract current focus from summary text"""
        # Look for current/focus/working keywords
        lines = summary_text.lower().split('\n')
        for line in lines:
            if any(keyword in line for keyword in ['current', 'focus', 'working on', 'now']):
                return line.strip()[:100]
        return "Continuing with task execution"

    def _extract_next_steps(self, summary_text: str) -> List[str]:
        """Extract next steps from summary text"""
        lines = summary_text.split('\n')
        next_steps = []
        in_next_section = False
        for line in lines:
            if any(keyword in line.lower() for keyword in ['next', 'upcoming', 'plan', 'todo']):
                in_next_section = True
                continue
            if in_next_section and (line.strip().startswith(('-', '*', '•')) or any(line.strip().startswith(f"{i}.") for i in range(1, 10))):
                next_steps.append(line.strip().lstrip('-*•0123456789. '))
        return next_steps[:3]

    def _compress_conversation_with_summary(self, messages: List[Dict]) -> List[Dict]:
        """Compress conversation using summary like Claude Code"""
        if not self.state.conversation_summaries:
            return messages
            
        # Keep system message + latest summary + recent messages
        latest_summary = self.state.conversation_summaries[-1]
        summary_text = f"""Previous Progress Summary:
Key accomplishments: {', '.join(latest_summary.key_accomplishments)}
Current focus: {latest_summary.current_focus}
Files: {', '.join(latest_summary.files_created_modified)}
Next steps: {', '.join(latest_summary.next_steps)}"""
        
        compressed = [
            messages[0],  # System message
            {"role": "user", "content": f"CONTEXT SUMMARY: {summary_text}"},
            *messages[-self.config.context_retention:]  # Recent messages
        ]
        
        return compressed

    def _track_progress(self, tool_name: str, tool_input: Dict, result: Dict):
        """Track progress after successful tool execution"""
        if tool_name == "bash":
            operation = f"Executed: {tool_input['command'][:50]}..."
        elif tool_name == "str_replace_editor":
            operation = f"File {tool_input['command']}: {tool_input['path']}"
        else:
            operation = f"Used tool: {tool_name}"
            
        if operation not in self.state.completed_steps:
            self.state.completed_steps.append(operation)

    def _get_user_guidance(self, tool_input: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Get user guidance with context"""
        step_description = tool_input["step_description"]
        status = tool_input["status"]
        error_details = tool_input.get("error_details", "")

        print(f"\n📋 Step: {step_description}")
        print(f"📊 Status: {status.upper()}")
        
        if error_details:
            print(f"❌ Error: {error_details}")

        user_response = input("Your guidance (continue/retry/skip): ").strip()
        return f"User guidance: {user_response}"

    def _process_user_guidance(self, guidance: str, tool_input: Dict[str, Any]):
        """Process user guidance"""
        if "skip" in guidance.lower():
            self.state.completed_steps.append(f"SKIPPED: {tool_input['step_description']}")

    def _format_tool_result(self, tool_name: str, result: Dict) -> str:
        """Format tool results"""
        if result["success"]:
            return f"✅ {tool_name} completed"
        else:
            return f"❌ {tool_name} failed: {result.get('error', 'Unknown error')}"

    def _get_current_context_summary(self) -> str:
        """Get current context for error handling"""
        return f"Step: {self.state.current_step}, Files: {len(self.state.files_tracking)}, Completed: {len(self.state.completed_steps)}"

    def _handle_error_with_context(self, error: Exception, messages: List[Dict]) -> str:
        """Handle error with contextual recovery"""
        print(f"🆘 Error during: {self.state.current_step}")
        print(f"Context: {self._get_current_context_summary()}")
        
        choice = input("Recovery (retry/skip/abort): ").strip().lower()
        return choice if choice in ["retry", "skip", "abort"] else "retry"

    def _create_completion_summary(self):
        """Create final completion summary"""
        if self.config.progress_tracking:
            self._update_progress_md_file()

    def _finalize_progress_md(self):
        """Finalize progress.md on completion"""
        try:
            with open(self.progress_path, "r") as f:
                content = f.read()
            
            content = content.replace("**Status:** In Progress", "**Status:** Completed ✅")
            content += f"\n\n## Task Completed\n**Completion Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"**Total Files Created/Modified:** {len(self.state.files_tracking)}\n"
            content += f"**Total Steps:** {len(self.state.completed_steps)}\n"
            
            with open(self.progress_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            print(f"⚠️ Could not finalize progress.md: {e}")

    def _build_summary_context(self) -> str:
        """Build context from summaries"""
        if not self.state.conversation_summaries:
            return ""
            
        latest = self.state.conversation_summaries[-1]
        return f"PREVIOUS PROGRESS: {', '.join(latest.key_accomplishments)} | CURRENT FOCUS: {latest.current_focus}"

    def _save_state(self):
        """Save enhanced state"""
        try:
            with open(self.state_path, 'wb') as f:
                pickle.dump(self.state, f)
        except Exception as e:
            print(f"⚠️ Could not save state: {e}")

    def _load_state(self, task_id: str) -> bool:
        """Load enhanced state"""
        try:
            if not self.state_path.exists():
                return False
            with open(self.state_path, 'rb') as f:
                loaded_state = pickle.load(f)
            if loaded_state.task_id == task_id:
                self.state = loaded_state
                return True
            return False
        except Exception:
            return False

    def _cleanup_state(self):
        """Clean up on completion"""
        try:
            if self.state_path.exists():
                self.state_path.unlink()
        except Exception:
            pass


def main():
    """Enhanced CLI with summarization"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced SWE Agent - Claude Code Summarization")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")  
    parser.add_argument("--max-iterations", type=int, default=30, help="Maximum iterations")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--resume", help="Resume task by ID")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress.md tracking")

    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return

    config = Config(
        api_key=api_key,
        working_dir=args.working_dir,
        max_iterations=args.max_iterations,
        debug_mode=args.debug,
        progress_tracking=not args.no_progress,
    )

    try:
        agent = EnhancedSummarizationAgent(config)
        
        if args.resume:
            result = agent.execute_task("", resume_task_id=args.resume)
        else:
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
        
        if config.progress_tracking:
            print(f"📋 Progress report: {config.progress_file}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted - state and progress saved")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()