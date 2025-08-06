"""
SWE Agent Ultimate - Complete Claude Code Equivalent  
Combines persistence, summarization, and full enhanced tool suite (12 tools)
The definitive production-ready software engineering agent
"""

import os
import json
import pickle
import glob
import re
import datetime
import requests
import subprocess
from typing import Dict, List, Any, Optional
from duckduckgo_search import DDGS
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
class UltimateAgentState:
    """Ultimate agent state with all capabilities"""
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
    sub_agent_results: List[Dict] = field(default_factory=list)  # Results from task_agent spawning


@dataclass
class Config:
    """Ultimate configuration with all features"""
    api_key: str
    working_dir: str = "."
    max_iterations: int = 50  # Higher for complex tasks
    debug_mode: bool = False
    state_file: str = ".swe_agent_ultimate_state.pkl"
    progress_file: str = "progress.md"
    context_retention: int = 8  # Conversation turns to keep
    summarization_threshold: int = 12  # Summarize after N iterations
    progress_tracking: bool = True
    enable_web: bool = True
    enable_notebooks: bool = True
    max_sub_agents: int = 3  # Limit concurrent sub-agents


def create_ultimate_tool_schema():
    """Complete tool schema with all 12+ enhanced tools"""
    return [
        # 1. Enhanced bash execution
        {
            "name": "bash",
            "description": "Execute bash commands with smart timeout and error recovery",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                    "timeout": {"type": "number", "description": "Command timeout in seconds", "default": 30}
                },
                "required": ["command"],
            },
        },
        
        # 2. Enhanced file operations  
        {
            "name": "str_replace_editor",
            "description": "Create, read, and edit files with advanced options and tracking",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "view", "view_range"],
                        "description": "The command to execute",
                    },
                    "path": {"type": "string", "description": "Path to the file"},
                    "file_text": {"type": "string", "description": "Content for create command"},
                    "old_str": {"type": "string", "description": "String to replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                    "view_range": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "[start_line, end_line]",
                    },
                },
                "required": ["command", "path"],
            },
        },
        
        # 3. File pattern search
        {
            "name": "glob_search", 
            "description": "Find files using patterns (like **/*.py, src/**/*.js)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to search for"},
                    "path": {"type": "string", "description": "Base path to search in", "default": "."},
                    "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                },
                "required": ["pattern"],
            },
        },
        
        # 4. Directory listing
        {
            "name": "list_directory",
            "description": "List directory contents with detailed information", 
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path", "default": "."},
                    "show_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
                    "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                },
            },
        },
        
        # 5. Text search within files
        {
            "name": "grep_search",
            "description": "Search for patterns within files using regex",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "File or directory to search in", "default": "."},
                    "file_pattern": {"type": "string", "description": "File pattern to limit search", "default": "*"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search", "default": True},
                    "context_lines": {"type": "number", "description": "Lines of context around matches", "default": 0},
                },
                "required": ["pattern"],
            },
        },
        
        # 6. Task management with visual feedback
        {
            "name": "todo_write",
            "description": "Create and manage task lists with progress tracking",
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
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            },
                            "required": ["id", "content", "status", "priority"],
                        },
                    }
                },
                "required": ["todos"],
            },
        },
        
        # 7. Sub-agent spawning for complex tasks
        {
            "name": "task_agent",
            "description": "Launch specialized sub-agents for complex analysis or tasks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Brief description of the task"},
                    "prompt": {"type": "string", "description": "Detailed prompt for the sub-agent"},
                    "agent_type": {
                        "type": "string",
                        "enum": ["search", "analysis", "coding", "debugging", "general"],
                        "description": "Type of specialized agent",
                        "default": "general",
                    },
                },
                "required": ["description", "prompt"],
            },
        },
        
        # 8. Web content fetching
        {
            "name": "web_fetch",
            "description": "Fetch and analyze web content for documentation and examples",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "prompt": {"type": "string", "description": "What to analyze in the content"},
                },
                "required": ["url", "prompt"],
            },
        },
        
        # 9. Web search capabilities
        {
            "name": "web_search", 
            "description": "Search the web for solutions and information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "number", "description": "Number of results", "default": 5},
                },
                "required": ["query"],
            },
        },
        
        # 10. Jupyter notebook support
        {
            "name": "notebook_edit",
            "description": "Create, read, and edit Jupyter notebooks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["create", "read", "add_cell", "edit_cell", "run_cell"],
                        "description": "Notebook operation",
                    },
                    "path": {"type": "string", "description": "Notebook path"},
                    "cell_content": {"type": "string", "description": "Cell content for add/edit"},
                    "cell_type": {"type": "string", "enum": ["code", "markdown"], "default": "code"},
                    "cell_index": {"type": "number", "description": "Cell index for edit operations"},
                },
                "required": ["command", "path"],
            },
        },
        
        # 11. Intelligent summarization
        {
            "name": "create_summary",
            "description": "Create intelligent summary of recent progress like Claude Code",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why creating summary"},
                    "key_accomplishments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Major things accomplished"
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
        
        # 12. Progress tracking
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
        
        # 13. User guidance and interaction
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
    ]


class UltimateSWEAgent:
    """Ultimate SWE Agent - Complete Claude Code equivalent with all capabilities"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.tools = create_ultimate_tool_schema()
        self.state: Optional[UltimateAgentState] = None
        self.active_sub_agents = 0
        
        # Filter tools based on config
        if not config.enable_web:
            self.tools = [t for t in self.tools if t["name"] not in ["web_fetch", "web_search"]]
        if not config.enable_notebooks:
            self.tools = [t for t in self.tools if t["name"] != "notebook_edit"]
        
        # Change to working directory
        if config.working_dir != ".":
            os.chdir(config.working_dir)
            
        self.state_path = Path(config.working_dir) / config.state_file
        self.progress_path = Path(config.working_dir) / config.progress_file
        
        print(f"🚀 Ultimate SWE Agent - Complete Claude Code Equivalent")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"🔧 Tools available: {len(self.tools)} tools")
        print(f"   📄 Files: str_replace_editor, glob_search, list_directory")
        print(f"   🔍 Search: grep_search")
        print(f"   ⚡ Execute: bash")
        print(f"   📝 Management: todo_write, create_summary, update_progress_md")
        print(f"   🤖 Advanced: task_agent, ask_user_step")
        if config.enable_web:
            print(f"   🌐 Web: web_fetch, web_search")
        if config.enable_notebooks:
            print(f"   📓 Notebooks: notebook_edit")
        print(f"💾 Progress file: {self.progress_path}")
        print(f"🧠 Auto-summarization: Every {config.summarization_threshold} iterations")

    def execute_task(self, task: str, resume_task_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute task with ultimate capabilities - persistence + summarization + full tools"""
        
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
            self.state = UltimateAgentState(
                task_id=task_id,
                original_task=task,
                completed_steps=[],
                current_step="Starting comprehensive task analysis",
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

        # Build ultimate system prompt
        system_prompt = self._build_ultimate_system_prompt()
        
        # Initialize or resume conversation with summaries
        messages = self._initialize_conversation(system_prompt, task)

        max_iterations = self.config.max_iterations
        
        while self.state.iteration_count < max_iterations:
            try:
                if self.config.debug_mode:
                    print(f"🔍 Iteration {self.state.iteration_count + 1}")
                    print(f"🎯 Current step: {self.state.current_step}")

                # Check if summarization is needed
                if (self.state.iteration_count > 0 and 
                    self.state.iteration_count % self.config.summarization_threshold == 0):
                    print(f"🧠 Creating intelligent summary after {self.state.iteration_count} iterations...")
                    self._create_intelligent_summary(messages)
                    messages = self._compress_conversation_with_summary(messages)

                # Get response with full tool suite
                response = self.client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=4000,
                    messages=messages,
                    tools=self.tools,
                )

                # Add response to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Handle tool use with all capabilities
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            print(f"⏺ {tool_name}()")
                            
                            # Execute with full tool suite
                            result = self._execute_ultimate_tool(tool_name, tool_input)
                            
                            # Handle user interaction
                            if (tool_name == "ask_user_step" and result["success"] 
                                and tool_input.get("status") in ["failed", "needs_guidance"]):
                                user_guidance = self._get_user_guidance(tool_input, result)
                                result["output"] = user_guidance
                                self._process_user_guidance(user_guidance, tool_input)
                            
                            # Display result like Claude Code
                            print(f"  ⎿ {self._format_tool_result(tool_name, result)}")
                            
                            # Track progress with full context
                            if result["success"]:
                                self._track_comprehensive_progress(tool_name, tool_input, result)

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
                    
                    # Create final comprehensive summary
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
                            "task_id": self.state.task_id,
                            "tools_used": len(self.tools),
                            "files_created": len(self.state.files_tracking),
                            "sub_agents_spawned": len(self.state.sub_agent_results)
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
                            "content": "Please continue working on the task with your full capabilities."
                        })

                self.state.iteration_count += 1
                self._save_state()

            except Exception as e:
                print(f"❌ Error in iteration {self.state.iteration_count + 1}: {e}")
                
                # Enhanced error handling with full context
                error_record = {
                    "iteration": self.state.iteration_count + 1,
                    "error": str(e),
                    "step": self.state.current_step,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "context": self._get_comprehensive_context_summary(),
                    "tools_available": [t["name"] for t in self.tools]
                }
                self.state.error_history.append(error_record)
                
                # Intelligent error recovery with full tool context
                recovery_action = self._handle_error_with_full_context(e, messages)
                
                if recovery_action == "abort":
                    self._save_state()
                    return {
                        "success": False,
                        "iterations": self.state.iteration_count + 1,
                        "error": str(e),
                        "task_id": self.state.task_id,
                        "resume_possible": True,
                        "tools_used": len(self.tools),
                        "comprehensive_state_saved": True
                    }
                elif recovery_action == "retry":
                    messages.append({
                        "role": "user",
                        "content": f"Error occurred: {e}. Please retry using your full tool suite and intelligence based on comprehensive progress so far."
                    })
                
                self.state.iteration_count += 1
                self._save_state()

        # Max iterations reached - create comprehensive final summary
        print("⚠️ Max iterations reached, creating comprehensive final summary...")
        self._create_completion_summary()
        self._save_state()
        
        return {
            "success": False,
            "iterations": max_iterations,
            "error": "Max iterations reached",
            "task_id": self.state.task_id,
            "resume_possible": True,
            "comprehensive_capabilities": True,
            "tools_available": len(self.tools)
        }

    def _build_ultimate_system_prompt(self) -> str:
        """Build comprehensive system prompt with all capabilities"""
        
        base_prompt = f"""You are the Ultimate Software Engineering Assistant - a complete Claude Code equivalent with comprehensive capabilities.

ULTIMATE CAPABILITIES:
You have access to the complete professional tool suite for software engineering:

📄 FILE OPERATIONS:
- str_replace_editor: Create, read, edit files with range viewing
- glob_search: Find files using patterns (**/*.py, src/**/*.js)  
- list_directory: Rich directory exploration with metadata

🔍 SEARCH & ANALYSIS:
- grep_search: Regex search across files with context
- task_agent: Spawn specialized sub-agents for complex analysis

⚡ EXECUTION & AUTOMATION:
- bash: Execute commands with intelligent timeout handling

📝 PROJECT MANAGEMENT:
- todo_write: Create interactive task lists with progress tracking
- create_summary: Intelligent context summarization like Claude Code
- update_progress_md: Comprehensive progress documentation

💬 USER INTERACTION:
- ask_user_step: Get user guidance on failures and decisions

🌐 WEB & RESEARCH: {f'''
- web_fetch: Fetch documentation, examples, tutorials
- web_search: Search for solutions and libraries''' if self.config.enable_web else 'Disabled'}

📓 DEVELOPMENT ENVIRONMENTS: {f'''
- notebook_edit: Full Jupyter notebook support''' if self.config.enable_notebooks else 'Disabled'}

INTELLIGENT BEHAVIOR:
1. **Comprehensive Task Analysis** - Use full tool suite to understand requirements
2. **Systematic Execution** - Break down complex tasks with todo_write
3. **Intelligent Search** - Use glob_search and grep_search to understand codebases
4. **Research Integration** - Leverage web tools for solutions and documentation
5. **Sub-agent Delegation** - Use task_agent for specialized complex analysis
6. **Progress Transparency** - Update progress.md and create summaries
7. **Error Recovery** - Handle failures gracefully with user guidance
8. **Context Management** - Use summarization to maintain long-term context

PERSISTENCE & RECOVERY:
- State is automatically saved after each major step
- You can resume from any interruption point
- Build on previous work instead of restarting
- Maintain comprehensive context across sessions"""

        # Add context from summaries if resuming
        if self.state and self.state.conversation_summaries:
            latest_summary = self.state.conversation_summaries[-1]
            context = f"""

PREVIOUS COMPREHENSIVE PROGRESS:
📝 Key accomplishments: {latest_summary.key_accomplishments}
🎯 Current focus: {latest_summary.current_focus}
📁 Files created/modified: {latest_summary.files_created_modified}
🛠️ Errors resolved: {latest_summary.errors_resolved}
➡️ Next steps: {latest_summary.next_steps}
🤖 Sub-agent results: {len(self.state.sub_agent_results)} completed

Continue building on this comprehensive progress."""
            base_prompt += context

        return base_prompt + f"\n\nWorking directory: {os.getcwd()}\nTools available: {len(self.tools)}"

    def _execute_ultimate_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools with ultimate capabilities"""
        
        try:
            if tool_name == "bash":
                return self._execute_enhanced_bash(tool_input["command"], tool_input.get("timeout", 30))
            elif tool_name == "str_replace_editor":
                return self._execute_enhanced_str_replace_editor(tool_input)
            elif tool_name == "glob_search":
                return self._execute_glob_search(tool_input)
            elif tool_name == "list_directory":
                return self._execute_list_directory(tool_input)
            elif tool_name == "grep_search":
                return self._execute_grep_search(tool_input)
            elif tool_name == "todo_write":
                return self._execute_todo_write(tool_input)
            elif tool_name == "task_agent":
                return self._execute_task_agent(tool_input)
            elif tool_name == "web_fetch":
                return self._execute_web_fetch(tool_input)
            elif tool_name == "web_search":
                return self._execute_web_search(tool_input)
            elif tool_name == "notebook_edit":
                return self._execute_notebook_edit(tool_input)
            elif tool_name == "create_summary":
                return self._execute_create_summary(tool_input)
            elif tool_name == "update_progress_md":
                return self._execute_update_progress_md(tool_input)
            elif tool_name == "ask_user_step":
                return {"success": True, "output": "User guidance requested"}
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_enhanced_bash(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Enhanced bash with intelligent timeout and tracking"""
        import subprocess
        
        # Intelligent timeout based on command type
        if any(cmd in command.lower() for cmd in ["install", "pip", "npm", "apt", "yum", "brew"]):
            timeout = min(300, timeout * 10)  # 5 minutes for installs
        elif any(cmd in command.lower() for cmd in ["git clone", "wget", "curl", "download"]):
            timeout = min(180, timeout * 6)  # 3 minutes for downloads
        elif any(cmd in command.lower() for cmd in ["test", "pytest", "npm test", "make test"]):
            timeout = min(120, timeout * 4)  # 2 minutes for tests
            
        try:
            print(f"  🔧 Running: {command}")
            if timeout > 60:
                print(f"  ⏱️ Extended timeout: {timeout}s for {command.split()[0]} operations")
                
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
                
                # Track any files that might have been created
                self._scan_for_new_files(command)

            return {
                "success": success,
                "output": output or "(No output)",
                "returncode": result.returncode,
                "command_type": self._classify_command(command),
                "timeout_used": timeout
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_enhanced_str_replace_editor(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced file operations with comprehensive tracking"""
        command = tool_input["command"]
        path = tool_input["path"]

        try:
            if command == "create":
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                content = tool_input.get("file_text", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Comprehensive file tracking
                self.state.files_tracking[path] = {
                    "created": datetime.datetime.now().isoformat(),
                    "size": len(content),
                    "lines": content.count('\n') + 1,
                    "action": "created",
                    "language": self._detect_language(path)
                }
                
                self.state.last_successful_operation = f"Created: {path}"
                return {"success": True, "output": f"Created file: {path} ({len(content)} chars, {content.count(chr(10)) + 1} lines)"}

            elif command == "view":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "success": True, 
                    "output": content,
                    "file_info": {
                        "size": len(content),
                        "lines": content.count('\n') + 1,
                        "language": self._detect_language(path)
                    }
                }

            elif command == "view_range":
                start_line, end_line = tool_input["view_range"]
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                content = "".join(lines[start_line - 1 : end_line])
                return {"success": True, "output": content}

            elif command == "str_replace":
                with open(path, "r", encoding="utf-8") as f:
                    original_content = f.read()

                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]

                if old_str not in original_content:
                    return {"success": False, "error": f"Text not found in {path}: {old_str[:50]}..."}

                new_content = original_content.replace(old_str, new_str)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # Track file modification
                self.state.files_tracking[path] = {
                    "modified": datetime.datetime.now().isoformat(),
                    "size": len(new_content),
                    "lines": new_content.count('\n') + 1,
                    "action": "modified",
                    "language": self._detect_language(path),
                    "changes": {
                        "old_size": len(original_content),
                        "new_size": len(new_content),
                        "diff": len(new_content) - len(original_content)
                    }
                }
                    
                self.state.last_successful_operation = f"Modified: {path}"
                return {"success": True, "output": f"Updated {path} (size changed by {len(new_content) - len(original_content)} chars)"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_glob_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced file pattern search"""
        try:
            pattern = tool_input["pattern"]
            base_path = tool_input.get("path", ".")
            recursive = tool_input.get("recursive", True)

            if recursive and "**" not in pattern:
                pattern = f"**/{pattern}"

            search_pattern = os.path.join(base_path, pattern)
            files = glob.glob(search_pattern, recursive=recursive)

            # Filter and categorize files
            files = [f for f in files if os.path.isfile(f)]
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Categorize by file type
            categorized = {}
            for file_path in files:
                ext = Path(file_path).suffix.lower()
                if ext not in categorized:
                    categorized[ext] = []
                categorized[ext].append(file_path)

            return {
                "success": True,
                "output": f"Found {len(files)} files matching '{pattern}':\n" + 
                         "\n".join(files[:20]) + 
                         (f"\n... and {len(files)-20} more files" if len(files) > 20 else ""),
                "file_count": len(files),
                "categories": categorized,
                "search_pattern": search_pattern
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_list_directory(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced directory listing with metadata"""
        try:
            path = tool_input.get("path", ".")
            show_hidden = tool_input.get("show_hidden", False)
            recursive = tool_input.get("recursive", False)

            items = []
            total_size = 0

            if recursive:
                for root, dirs, files in os.walk(path):
                    if not show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        files = [f for f in files if not f.startswith(".")]

                    for name in dirs + files:
                        full_path = os.path.join(root, name)
                        rel_path = os.path.relpath(full_path, path)
                        is_dir = os.path.isdir(full_path)
                        size = 0 if is_dir else os.path.getsize(full_path)
                        total_size += size
                        
                        items.append({
                            "name": rel_path,
                            "type": "directory" if is_dir else "file",
                            "size": size,
                            "language": None if is_dir else self._detect_language(full_path)
                        })
            else:
                for item in os.listdir(path):
                    if not show_hidden and item.startswith("."):
                        continue
                        
                    full_path = os.path.join(path, item)
                    is_dir = os.path.isdir(full_path)
                    size = 0 if is_dir else os.path.getsize(full_path)
                    total_size += size
                    
                    items.append({
                        "name": item,
                        "type": "directory" if is_dir else "file", 
                        "size": size,
                        "language": None if is_dir else self._detect_language(full_path)
                    })

            # Sort by type then name
            items.sort(key=lambda x: (x["type"], x["name"]))

            output = f"📁 Directory: {path}\n"
            output += f"Total items: {len(items)}, Total size: {total_size} bytes\n\n"
            
            for item in items:
                icon = "📁" if item["type"] == "directory" else "📄"
                size_str = "" if item["type"] == "directory" else f" ({item['size']} bytes)"
                lang_str = "" if not item["language"] else f" [{item['language']}]"
                output += f"{icon} {item['name']}{size_str}{lang_str}\n"

            return {
                "success": True,
                "output": output,
                "items": items,
                "total_size": total_size
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_grep_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced regex search with context"""
        try:
            pattern = tool_input["pattern"]
            search_path = tool_input.get("path", ".")
            file_pattern = tool_input.get("file_pattern", "*")
            case_sensitive = tool_input.get("case_sensitive", True)
            context_lines = tool_input.get("context_lines", 0)

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            matches = []
            files_searched = 0

            # Find files to search
            if os.path.isfile(search_path):
                files_to_search = [search_path]
            else:
                files_to_search = glob.glob(
                    os.path.join(search_path, "**", file_pattern), recursive=True
                )
                files_to_search = [f for f in files_to_search if os.path.isfile(f)]

            for file_path in files_to_search:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    files_searched += 1

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            match_info = {
                                "file": file_path,
                                "line_number": i + 1,
                                "line": line.strip(),
                                "language": self._detect_language(file_path)
                            }
                            
                            # Add context if requested
                            if context_lines > 0:
                                context = []
                                start = max(0, i - context_lines)
                                end = min(len(lines), i + context_lines + 1)
                                for j in range(start, end):
                                    if j != i:
                                        context.append(f"{j+1}: {lines[j].strip()}")
                                match_info["context"] = context
                            
                            matches.append(match_info)

                except Exception:
                    continue

            # Format output
            output = f"🔍 Pattern: '{pattern}' (case {'sensitive' if case_sensitive else 'insensitive'})\n"
            output += f"Files searched: {files_searched}, Matches found: {len(matches)}\n\n"
            
            for i, match in enumerate(matches[:15]):  # Limit display
                output += f"📄 {match['file']}:{match['line_number']}: {match['line']}\n"
                if match.get("context"):
                    for ctx in match["context"]:
                        output += f"     {ctx}\n"
                    output += "\n"
            
            if len(matches) > 15:
                output += f"... and {len(matches) - 15} more matches"

            return {
                "success": True,
                "output": output,
                "matches": matches,
                "files_searched": files_searched
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_todo_write(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced todo management with comprehensive tracking"""
        try:
            todos_data = tool_input["todos"]

            # Update internal state
            current_todos = {}
            for todo in todos_data:
                current_todos[todo["id"]] = todo

            # Display like Claude Code with enhancements
            output = "⏺ Update Todos\n"
            status_counts = {"pending": 0, "in_progress": 0, "completed": 0}
            
            for todo in todos_data:
                status_symbol = {"pending": "☐", "in_progress": "🔄", "completed": "☒"}
                symbol = status_symbol.get(todo["status"], "☐")
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                priority = priority_emoji.get(todo["priority"], "")
                output += f"  ⎿  {symbol} {todo['content']} {priority}\n"
                status_counts[todo["status"]] = status_counts.get(todo["status"], 0) + 1

            output += f"\nSummary: {status_counts['completed']} completed, {status_counts['in_progress']} in progress, {status_counts['pending']} pending\n"

            print(output)  # Display immediately

            return {
                "success": True, 
                "output": output,
                "status_counts": status_counts,
                "total_todos": len(todos_data)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_task_agent(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn intelligent sub-agents with result tracking"""
        try:
            description = tool_input["description"]
            prompt = tool_input["prompt"]
            agent_type = tool_input.get("agent_type", "general")

            # Check sub-agent limits
            if self.active_sub_agents >= self.config.max_sub_agents:
                return {
                    "success": False, 
                    "error": f"Maximum sub-agents ({self.config.max_sub_agents}) already active"
                }

            print(f"🤖 Spawning {agent_type} sub-agent: {description}")
            self.active_sub_agents += 1

            try:
                # Create specialized sub-agent
                sub_config = Config(
                    api_key=self.config.api_key,
                    working_dir=self.config.working_dir,
                    max_iterations=8,  # Limit sub-agent iterations
                    debug_mode=False,
                    enable_web=agent_type in ["research", "general"],  # Enable web for research agents
                    enable_notebooks=agent_type in ["analysis", "general"]
                )

                # Create sub-agent with specialized tools
                sub_agent = UltimateSWEAgent.__new__(UltimateSWEAgent)
                sub_agent.config = sub_config
                sub_agent.client = self.client
                sub_agent.active_sub_agents = 0
                
                # Filter tools based on agent type
                if agent_type == "search":
                    sub_agent.tools = [t for t in self.tools if t["name"] in 
                                     ["glob_search", "grep_search", "list_directory", "str_replace_editor"]]
                elif agent_type == "analysis":
                    sub_agent.tools = [t for t in self.tools if t["name"] in 
                                     ["str_replace_editor", "grep_search", "bash", "create_summary"]]
                elif agent_type == "coding":
                    sub_agent.tools = [t for t in self.tools if t["name"] in 
                                     ["str_replace_editor", "bash", "glob_search", "grep_search"]]
                elif agent_type == "debugging":
                    sub_agent.tools = [t for t in self.tools if t["name"] in 
                                     ["str_replace_editor", "bash", "grep_search", "list_directory"]]
                else:
                    sub_agent.tools = self.tools[:6]  # Basic comprehensive set

                sub_agent.state = None  # Fresh state for sub-agent
                
                result = sub_agent.execute_task(prompt)

                # Track sub-agent result
                sub_result = {
                    "agent_type": agent_type,
                    "description": description,
                    "success": result["success"],
                    "iterations": result["iterations"],
                    "response": result.get("final_response", ""),
                    "timestamp": datetime.datetime.now().isoformat()
                }
                self.state.sub_agent_results.append(sub_result)

                return {
                    "success": result["success"],
                    "output": f"Sub-agent ({agent_type}) completed in {result['iterations']} iterations:\n{result.get('final_response', 'No response')[:500]}{'...' if len(str(result.get('final_response', ''))) > 500 else ''}",
                    "sub_agent_result": sub_result
                }

            finally:
                self.active_sub_agents -= 1

        except Exception as e:
            self.active_sub_agents -= 1
            return {"success": False, "error": str(e)}

    def _execute_web_fetch(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced web content fetching with analysis"""
        try:
            url = tool_input["url"]
            prompt = tool_input["prompt"]

            print(f"  🌐 Fetching: {url}")
            
            # Fetch with proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            
            content = response.text[:8000]  # Limit content for analysis

            return {
                "success": True,
                "output": f"📄 Fetched from {url} ({len(content)} chars)\n\nContent preview:\n{content[:1000]}{'...' if len(content) > 1000 else ''}\n\nAnalysis prompt: {prompt}",
                "url": url,
                "content_length": len(content),
                "status_code": response.status_code
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to fetch {url}: {str(e)}"}

def _execute_web_search(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced web search using DuckDuckGo with result formatting"""
    try:
        query = tool_input["query"]
        num_results = tool_input.get("num_results", 5)

        print(f"  🔍 Searching: {query}")

        results = []
        with DDGS() as ddgs:
            for i, result in enumerate(ddgs.text(query, max_results=num_results)):
                results.append(result)
                if i + 1 >= num_results:
                    break

        if not results:
            return {
                "success": False,
                "error": "No results found or query failed."
            }

        formatted_results = "\n\n".join(
            [f"{i+1}. [{res['title']}]({res['href']})\n{res['body']}"
             for i, res in enumerate(results)]
        )

        return {
            "success": True,
            "output": f"🔍 Web search results for '{query}':\n\n{formatted_results}",
            "query": query,
            "placeholder": False
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

def _execute_notebook_edit(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced Jupyter notebook operations"""
    try:
        command = tool_input["command"]
        path = tool_input["path"]

        if command == "create":
            notebook = {
                "cells": [],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5
            }
            return {"success": True, "output": notebook}

    except Exception as e:
        return {"success": False, "error": str(e)}


    def _execute_web_search(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced web search with result formatting"""
        try:
            query = tool_input["query"]
            num_results = tool_input.get("num_results", 5)

            print(f"  🔍 Searching: {query}")

            # Placeholder for actual search implementation
            # In production, would integrate with search APIs
            return {
                "success": True,
                "output": f"🔍 Web search for '{query}' would return {num_results} results\n\nNote: This is a placeholder. In production, would integrate with:\n- Google Custom Search API\n- Bing Search API\n- DuckDuckGo API\n\nFor development, use web_fetch with specific URLs for documentation.",
                "query": query,
                "placeholder": True
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_notebook_edit(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced Jupyter notebook operations"""
        try:
            command = tool_input["command"]
            path = tool_input["path"]

            if command == "create":
                notebook = {
                    "cells": [],
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Python 3",
                            "language": "python",
                            "name": "python3"
                        },
                        "language_info": {
                            "name": "python",
                            "version": "3.8.0"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 4,
                }
                
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w") as f:
                    json.dump(notebook, f, indent=2)
                
                # Track notebook creation
                self.state.files_tracking[path] = {
                    "created": datetime.datetime.now().isoformat(),
                    "size": len(json.dumps(notebook)),
                    "action": "created",
                    "type": "jupyter_notebook"
                }
                
                return {"success": True, "output": f"Created Jupyter notebook: {path}"}

            elif command == "read":
                with open(path, "r") as f:
                    notebook = json.load(f)
                    
                cell_count = len(notebook.get("cells", []))
                cell_types = {}
                for cell in notebook.get("cells", []):
                    cell_type = cell.get("cell_type", "unknown")
                    cell_types[cell_type] = cell_types.get(cell_type, 0) + 1
                
                return {
                    "success": True,
                    "output": f"📓 Notebook: {path}\nCells: {cell_count} total ({dict(cell_types)})",
                    "cell_count": cell_count,
                    "cell_types": cell_types
                }

            elif command == "add_cell":
                cell_content = tool_input.get("cell_content", "")
                cell_type = tool_input.get("cell_type", "code")
                
                with open(path, "r") as f:
                    notebook = json.load(f)
                
                new_cell = {
                    "cell_type": cell_type,
                    "source": cell_content.split('\n'),
                    "metadata": {}
                }
                
                if cell_type == "code":
                    new_cell["execution_count"] = None
                    new_cell["outputs"] = []
                
                notebook["cells"].append(new_cell)
                
                with open(path, "w") as f:
                    json.dump(notebook, f, indent=2)
                
                return {
                    "success": True,
                    "output": f"Added {cell_type} cell to {path} (now {len(notebook['cells'])} cells)"
                }

            else:
                return {"success": False, "error": f"Notebook command '{command}' not implemented"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_summary(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intelligent summarization like Claude Code"""
        try:
            reason = tool_input["reason"]
            key_accomplishments = tool_input["key_accomplishments"]
            current_focus = tool_input["current_focus"]
            next_steps = tool_input.get("next_steps", [])
            
            # Create comprehensive summary
            summary_id = f"ultimate_{len(self.state.conversation_summaries) + 1}"
            conversation_summary = ConversationSummary(
                summary_id=summary_id,
                iterations_covered=(max(0, self.state.iteration_count - 8), self.state.iteration_count),
                key_accomplishments=key_accomplishments,
                current_focus=current_focus,
                next_steps=next_steps,
                files_created_modified=list(self.state.files_tracking.keys()),
                errors_resolved=[err.get('error', '')[:50] for err in self.state.error_history[-3:]],
                timestamp=datetime.datetime.now().isoformat()
            )
            
            self.state.conversation_summaries.append(conversation_summary)
            
            return {
                "success": True,
                "output": f"📋 Comprehensive Summary Created\nReason: {reason}\nAccomplishments: {len(key_accomplishments)}\nFiles tracked: {len(self.state.files_tracking)}\nSub-agents used: {len(self.state.sub_agent_results)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_update_progress_md(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Update comprehensive progress tracking"""
        try:
            action = tool_input["action"]
            files_modified = tool_input.get("files_modified", [])
            
            # Track files with enhanced metadata
            for file_path in files_modified:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    self.state.files_tracking[file_path] = {
                        "last_modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size,
                        "action": action,
                        "language": self._detect_language(file_path)
                    }
            
            # Add comprehensive progress entry
            progress_entry = ProgressEntry(
                timestamp=datetime.datetime.now().isoformat(),
                action=action,
                details=f"Modified {len(files_modified)} files" if files_modified else "Action completed with full tool suite",
                files_affected=files_modified,
                status="completed"
            )
            
            self.state.progress_entries.append(progress_entry)
            
            # Update comprehensive progress.md
            self._update_progress_md_file()
            
            return {
                "success": True,
                "output": f"📊 Progress Updated: {action}\nFiles tracked: {len(files_modified)}\nTotal files: {len(self.state.files_tracking)}\nSub-agents: {len(self.state.sub_agent_results)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Helper methods for comprehensive functionality
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
            '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
            '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.html': 'html', '.css': 'css', '.scss': 'scss',
            '.md': 'markdown', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.xml': 'xml', '.sql': 'sql', '.sh': 'shell', '.bat': 'batch'
        }
        return language_map.get(ext, 'unknown')

    def _classify_command(self, command: str) -> str:
        """Classify bash command type for intelligent handling"""
        command_lower = command.lower().strip()
        
        if any(cmd in command_lower for cmd in ["install", "pip", "npm", "apt", "brew"]):
            return "package_management"
        elif any(cmd in command_lower for cmd in ["git", "clone", "commit", "push", "pull"]):
            return "version_control"
        elif any(cmd in command_lower for cmd in ["test", "pytest", "npm test", "make test"]):
            return "testing"
        elif any(cmd in command_lower for cmd in ["build", "compile", "make", "webpack"]):
            return "build"
        elif any(cmd in command_lower for cmd in ["ls", "dir", "pwd", "whoami", "date"]):
            return "system_info"
        else:
            return "general"

    def _scan_for_new_files(self, command: str):
        """Scan for files created by bash commands"""
        if any(pattern in command.lower() for pattern in ["touch", "echo >", "cat >", "mkdir", "cp", "mv"]):
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
                                    "action": "created_by_command",
                                    "language": self._detect_language(file_str)
                                }
            except Exception:
                pass  # Ignore scan errors

    def _initialize_progress_md(self):
        """Initialize comprehensive progress.md file"""
        content = f"""# Ultimate SWE Agent Progress Report

**Task ID:** `{self.state.task_id}`  
**Started:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Agent Version:** Ultimate (Complete Claude Code Equivalent)  
**Tools Available:** {len(self.tools)} professional tools  
**Status:** In Progress

## Task Description
{self.state.original_task}

## Agent Capabilities
✅ **File Operations:** str_replace_editor, glob_search, list_directory  
✅ **Search & Analysis:** grep_search, task_agent spawning  
✅ **Execution:** bash with intelligent timeouts  
✅ **Project Management:** todo_write, create_summary, update_progress_md  
✅ **User Interaction:** ask_user_step for guidance  
{f'✅ **Web Research:** web_fetch, web_search' if self.config.enable_web else '❌ **Web Research:** Disabled'}  
{f'✅ **Jupyter Notebooks:** notebook_edit' if self.config.enable_notebooks else '❌ **Jupyter Notebooks:** Disabled'}  

## Progress Timeline

"""
        with open(self.progress_path, "w") as f:
            f.write(content)

    def _update_progress_md_file(self):
        """Update progress.md with comprehensive tracking"""
        if not self.config.progress_tracking:
            return
            
        try:
            content = f"""# Ultimate SWE Agent Progress Report

**Task ID:** `{self.state.task_id}`  
**Started:** {self.state.progress_entries[0].timestamp if self.state.progress_entries else 'Unknown'}  
**Last Updated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Agent Version:** Ultimate (Complete Claude Code Equivalent)  
**Tools Available:** {len(self.tools)} professional tools  
**Status:** {'Completed' if len(self.state.completed_steps) > 10 else 'In Progress'}  
**Iterations:** {self.state.iteration_count}

## Task Description
{self.state.original_task}

## Ultimate Agent Capabilities
✅ **File Operations:** str_replace_editor (create/edit/view), glob_search, list_directory  
✅ **Search & Analysis:** grep_search with regex, task_agent spawning  
✅ **Execution:** bash with intelligent timeouts and classification  
✅ **Project Management:** todo_write, create_summary, update_progress_md  
✅ **User Interaction:** ask_user_step for error recovery guidance  
{f'✅ **Web Research:** web_fetch, web_search for documentation' if self.config.enable_web else '❌ **Web Research:** Disabled'}  
{f'✅ **Jupyter Notebooks:** notebook_edit for data science' if self.config.enable_notebooks else '❌ **Jupyter Notebooks:** Disabled'}  

## Comprehensive Summaries
"""
            
            # Add intelligent summaries
            for summary in self.state.conversation_summaries:
                content += f"\n### {summary.summary_id} ({summary.timestamp[:19]})\n"
                content += f"**Iterations:** {summary.iterations_covered[0]}-{summary.iterations_covered[1]}\n\n"
                content += "**Key Accomplishments:**\n"
                for acc in summary.key_accomplishments:
                    content += f"- {acc}\n"
                content += f"\n**Current Focus:** {summary.current_focus}\n"
                if summary.next_steps:
                    content += "**Next Steps:**\n"
                    for step in summary.next_steps:
                        content += f"- {step}\n"
                content += "\n"
            
            content += "\n## Files Created/Modified (Enhanced Tracking)\n\n"
            for file_path, info in self.state.files_tracking.items():
                action = info.get('action', 'unknown')
                timestamp = info.get('created') or info.get('modified', 'unknown')
                size = info.get('size', 0)
                language = info.get('language', 'unknown')
                lines = info.get('lines', 'N/A')
                content += f"- **{file_path}** - {action} ({timestamp[:19]}, {size} bytes, {lines} lines, {language})\n"
            
            content += f"\n## Sub-Agent Results ({len(self.state.sub_agent_results)})\n\n"
            for i, result in enumerate(self.state.sub_agent_results, 1):
                status = "✅" if result["success"] else "❌"
                content += f"{i}. {status} **{result['agent_type']}** - {result['description']} ({result['iterations']} iterations)\n"
                content += f"   Response: {result['response'][:100]}{'...' if len(result['response']) > 100 else ''}\n\n"
            
            content += "\n## Detailed Timeline\n\n"
            for entry in self.state.progress_entries:
                status_emoji = {"completed": "✅", "failed": "❌", "skipped": "⏭️"}.get(entry.status, "🔄")
                content += f"### {entry.timestamp[:19]} {status_emoji}\n"
                content += f"**Action:** {entry.action}\n"
                content += f"**Details:** {entry.details}\n"
                if entry.files_affected:
                    content += f"**Files:** {', '.join(entry.files_affected)}\n"
                content += "\n"
            
            # Add comprehensive error history
            if self.state.error_history:
                content += "## Error History & Recovery\n\n"
                for error in self.state.error_history:
                    content += f"- **{error['timestamp'][:19]}** - Iteration {error['iteration']}\n"
                    content += f"  - **Step:** {error['step']}\n"
                    content += f"  - **Error:** {error['error'][:100]}{'...' if len(error['error']) > 100 else ''}\n"
                    content += f"  - **Context:** {error.get('context', 'No context')}\n\n"
            
            # Add tool usage statistics
            content += f"## Tool Usage Statistics\n\n"
            content += f"- **Total Tools Available:** {len(self.tools)}\n"
            content += f"- **Files Tracked:** {len(self.state.files_tracking)}\n"
            content += f"- **Sub-Agents Spawned:** {len(self.state.sub_agent_results)}\n"
            content += f"- **Summaries Created:** {len(self.state.conversation_summaries)}\n"
            content += f"- **Errors Encountered:** {len(self.state.error_history)}\n"
            content += f"- **Progress Entries:** {len(self.state.progress_entries)}\n"
            
            with open(self.progress_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            print(f"⚠️ Could not update progress.md: {e}")

    # Additional helper methods from previous implementations...
    def _initialize_conversation(self, system_prompt: str, task: str) -> List[Dict]:
        """Initialize conversation with comprehensive context"""
        if self.state.conversation_summaries:
            summary_context = self._build_comprehensive_summary_context()
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{summary_context}\n\nContinue task with full capabilities: {task}"}]
        else:
            messages = [{"role": "user", "content": f"{system_prompt}\n\nTask: {task}"}]
        
        return messages

    def _build_comprehensive_summary_context(self) -> str:
        """Build comprehensive context from summaries"""
        if not self.state.conversation_summaries:
            return ""
            
        latest = self.state.conversation_summaries[-1]
        return f"""COMPREHENSIVE PREVIOUS PROGRESS:
📝 Accomplishments: {', '.join(latest.key_accomplishments)}
🎯 Current Focus: {latest.current_focus}
📁 Files: {', '.join(latest.files_created_modified)}
🤖 Sub-agents: {len(self.state.sub_agent_results)} completed
🛠️ Errors resolved: {', '.join(latest.errors_resolved)}
➡️ Next: {', '.join(latest.next_steps)}"""

    def _create_intelligent_summary(self, messages: List[Dict]):
        """Create comprehensive intelligent summary"""
        try:
            # Use Claude to analyze recent progress
            recent_messages = messages[-10:]
            
            summary_prompt = """Analyze this Ultimate SWE Agent conversation and create a comprehensive summary:
1. Key accomplishments with technical details
2. Current focus and technical context
3. Files created/modified and their purposes  
4. Any errors resolved and solutions found
5. Next logical steps with specific actions
6. Tool usage patterns and effectiveness

Be comprehensive but concise - this summary will guide future work."""
            
            summary_response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": summary_prompt},
                    {"role": "assistant", "content": str(recent_messages)}
                ]
            )
            
            summary_text = summary_response.content[0].text if summary_response.content else ""
            
            # Create structured comprehensive summary
            summary_id = f"ultimate_summary_{len(self.state.conversation_summaries) + 1}"
            conversation_summary = ConversationSummary(
                summary_id=summary_id,
                iterations_covered=(max(0, self.state.iteration_count - 10), self.state.iteration_count),
                key_accomplishments=self._extract_accomplishments(summary_text),
                current_focus=self._extract_current_focus(summary_text),
                next_steps=self._extract_next_steps(summary_text),
                files_created_modified=list(self.state.files_tracking.keys()),
                errors_resolved=[err.get('error', '')[:50] for err in self.state.error_history[-5:]],
                timestamp=datetime.datetime.now().isoformat()
            )
            
            self.state.conversation_summaries.append(conversation_summary)
            
            print(f"📋 Ultimate Summary: {len(conversation_summary.key_accomplishments)} accomplishments, {len(self.state.files_tracking)} files, {len(self.state.sub_agent_results)} sub-agents")
            
        except Exception as e:
            print(f"⚠️ Could not create comprehensive summary: {e}")

    def _compress_conversation_with_summary(self, messages: List[Dict]) -> List[Dict]:
        """Compress conversation using comprehensive summary"""
        if not self.state.conversation_summaries:
            return messages
            
        latest_summary = self.state.conversation_summaries[-1]
        summary_text = f"""ULTIMATE AGENT COMPREHENSIVE SUMMARY:
Key accomplishments: {', '.join(latest_summary.key_accomplishments)}
Current focus: {latest_summary.current_focus}
Files tracked: {len(latest_summary.files_created_modified)} ({', '.join(latest_summary.files_created_modified[:5])}{' ...' if len(latest_summary.files_created_modified) > 5 else ''})
Sub-agents used: {len(self.state.sub_agent_results)}
Errors resolved: {', '.join(latest_summary.errors_resolved)}
Next steps: {', '.join(latest_summary.next_steps)}
Tools available: {len(self.tools)} professional tools"""
        
        compressed = [
            messages[0],  # System message
            {"role": "user", "content": f"COMPREHENSIVE CONTEXT: {summary_text}"},
            *messages[-self.config.context_retention:]  # Recent messages
        ]
        
        return compressed

    def _get_comprehensive_context_summary(self) -> str:
        """Get comprehensive context for error handling"""
        return f"""Step: {self.state.current_step}
Files: {len(self.state.files_tracking)}
Completed: {len(self.state.completed_steps)}
Sub-agents: {len(self.state.sub_agent_results)}
Tools: {len(self.tools)}
Summaries: {len(self.state.conversation_summaries)}"""

    def _handle_error_with_full_context(self, error: Exception, messages: List[Dict]) -> str:
        """Handle error with comprehensive context"""
        print(f"🆘 Error during: {self.state.current_step}")
        print(f"Comprehensive context: {self._get_comprehensive_context_summary()}")
        print(f"Available tools: {[t['name'] for t in self.tools]}")
        print(f"Sub-agents available: {self.config.max_sub_agents - self.active_sub_agents}")
        
        print("\nRecovery options:")
        print("1. retry - Try again with full tool suite")
        print("2. delegate - Spawn sub-agent to handle this issue") 
        print("3. skip - Skip this step and continue")
        print("4. abort - Save comprehensive state and exit")
        
        choice = input("Recovery choice (1-4): ").strip().lower()
        
        if choice == "2" or choice == "delegate":
            print("Would spawn debugging sub-agent to analyze and resolve the error...")
        
        return {"1": "retry", "2": "retry", "3": "skip", "4": "abort"}.get(choice, "retry")

    def _track_comprehensive_progress(self, tool_name: str, tool_input: Dict, result: Dict):
        """Track progress with comprehensive metadata"""
        if tool_name == "bash":
            operation = f"Executed {self._classify_command(tool_input['command'])}: {tool_input['command'][:50]}..."
        elif tool_name == "str_replace_editor":
            operation = f"File {tool_input['command']}: {tool_input['path']}"
        elif tool_name == "task_agent":
            operation = f"Spawned {tool_input.get('agent_type', 'general')} sub-agent: {tool_input['description'][:50]}..."
        elif tool_name in ["glob_search", "grep_search"]:
            operation = f"Search with {tool_name}: {tool_input.get('pattern', 'N/A')}"
        else:
            operation = f"Used {tool_name}: {list(tool_input.keys())}"
            
        if operation not in self.state.completed_steps:
            self.state.completed_steps.append(operation)

    def _get_user_guidance(self, tool_input: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Get user guidance with comprehensive context"""
        step_description = tool_input["step_description"]
        status = tool_input["status"]
        error_details = tool_input.get("error_details", "")
        suggested_action = tool_input.get("suggested_next_action", "")

        print(f"\n📋 Step: {step_description}")
        print(f"📊 Status: {status.upper()}")
        print(f"🔧 Tools available: {len(self.tools)}")
        print(f"🤖 Sub-agents available: {self.config.max_sub_agents - self.active_sub_agents}")
        
        if error_details:
            print(f"❌ Error: {error_details}")
        if suggested_action:
            print(f"💡 Suggested: {suggested_action}")

        if status == "failed":
            print("\n❓ How should the Ultimate Agent handle this failure?")
            print("1. retry - Use full tool suite to try again")
            print("2. delegate - Spawn specialized sub-agent")  
            print("3. research - Use web tools to find solution")
            print("4. skip - Mark as skipped and continue")
            print("5. manual - I'll handle this manually")
        else:
            print("\n❓ How should the Ultimate Agent proceed?")
            print("1. continue - Proceed with full capabilities")
            print("2. focus - Focus on specific aspect")
            print("3. delegate - Spawn sub-agent for next steps")

        choice = input("Your guidance: ").strip()
        additional_info = ""
        
        if choice in ["2", "delegate", "focus"]:
            additional_info = input("What should be the focus/delegation? ")
        elif choice in ["5", "manual"]:
            additional_info = input("What did you do manually? ")
            
        return f"User chose '{choice}' with Ultimate Agent context. Additional info: {additional_info}"

    def _process_user_guidance(self, guidance: str, tool_input: Dict[str, Any]):
        """Process user guidance with comprehensive tracking"""
        if "skip" in guidance.lower():
            self.state.completed_steps.append(f"SKIPPED: {tool_input['step_description']}")
        elif "manual" in guidance.lower():
            self.state.completed_steps.append(f"MANUAL: {tool_input['step_description']}")
        elif "delegate" in guidance.lower():
            self.state.completed_steps.append(f"DELEGATED: {tool_input['step_description']}")

    def _format_tool_result(self, tool_name: str, result: Dict) -> str:
        """Format tool results with comprehensive info"""
        if result["success"]:
            if tool_name == "bash":
                cmd_type = result.get("command_type", "general")
                return f"✅ Command executed ({cmd_type})"
            elif tool_name == "task_agent":
                return f"✅ Sub-agent completed: {result.get('sub_agent_result', {}).get('agent_type', 'unknown')}"
            elif tool_name in ["glob_search", "grep_search"]:
                count = result.get("file_count", result.get("matches", 0))
                return f"✅ Search completed ({count} results)"
            elif tool_name == "str_replace_editor":
                return f"✅ File operation completed"
            else:
                return f"✅ {tool_name} completed"
        else:
            return f"❌ {tool_name} failed: {result.get('error', 'Unknown error')}"

    def _create_completion_summary(self):
        """Create comprehensive completion summary"""
        if self.config.progress_tracking:
            self._update_progress_md_file()
            
        print(f"\n📊 Ultimate Agent Task Summary:")
        print(f"✅ Files created/modified: {len(self.state.files_tracking)}")
        print(f"🤖 Sub-agents spawned: {len(self.state.sub_agent_results)}")
        print(f"📝 Progress entries: {len(self.state.progress_entries)}")
        print(f"🧠 Summaries created: {len(self.state.conversation_summaries)}")
        print(f"🔧 Tools available: {len(self.tools)}")

    def _finalize_progress_md(self):
        """Finalize comprehensive progress.md on completion"""
        try:
            with open(self.progress_path, "r") as f:
                content = f.read()
            
            content = content.replace("**Status:** In Progress", "**Status:** Completed ✅")
            content += f"\n\n## Task Completed Successfully\n"
            content += f"**Completion Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"**Ultimate Agent Performance:**\n"
            content += f"- **Total Files Created/Modified:** {len(self.state.files_tracking)}\n"
            content += f"- **Total Steps Completed:** {len(self.state.completed_steps)}\n"
            content += f"- **Sub-Agents Utilized:** {len(self.state.sub_agent_results)}\n"
            content += f"- **Intelligent Summaries:** {len(self.state.conversation_summaries)}\n"
            content += f"- **Tools Available:** {len(self.tools)} professional tools\n"
            content += f"- **Error Recovery Events:** {len(self.state.error_history)}\n"
            content += f"\n**Agent Capabilities Utilized:**\n"
            content += f"✅ Complete Claude Code equivalent functionality achieved\n"
            
            with open(self.progress_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            print(f"⚠️ Could not finalize progress.md: {e}")

    # Additional helper methods for extraction (same as previous implementations)
    def _extract_accomplishments(self, summary_text: str) -> List[str]:
        """Extract key accomplishments from summary text"""
        lines = summary_text.split('\n')
        accomplishments = []
        for line in lines:
            if line.strip().startswith(('-', '*', '•')) or any(line.strip().startswith(f"{i}.") for i in range(1, 10)):
                accomplishments.append(line.strip().lstrip('-*•0123456789. '))
        return accomplishments[:5]

    def _extract_current_focus(self, summary_text: str) -> str:
        """Extract current focus from summary text"""
        lines = summary_text.lower().split('\n')
        for line in lines:
            if any(keyword in line for keyword in ['current', 'focus', 'working on', 'now']):
                return line.strip()[:100]
        return "Continuing comprehensive task execution"

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

    def _save_state(self):
        """Save comprehensive ultimate state"""
        try:
            with open(self.state_path, 'wb') as f:
                pickle.dump(self.state, f)
            if self.config.debug_mode:
                print(f"💾 Ultimate state saved: {len(self.state.files_tracking)} files, {len(self.state.sub_agent_results)} sub-agents")
        except Exception as e:
            print(f"⚠️ Could not save ultimate state: {e}")

    def _load_state(self, task_id: str) -> bool:
        """Load comprehensive ultimate state"""
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
            print(f"⚠️ Could not load ultimate state: {e}")
            return False

    def _cleanup_state(self):
        """Clean up state on successful completion"""
        try:
            if self.state_path.exists():
                self.state_path.unlink()
                print(f"🧹 Ultimate state cleaned up")
        except Exception:
            pass


def main():
    """Ultimate CLI entry point with comprehensive capabilities"""
    import argparse

    parser = argparse.ArgumentParser(description="Ultimate SWE Agent - Complete Claude Code Equivalent")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--working-dir", default=".", help="Working directory")  
    parser.add_argument("--max-iterations", type=int, default=50, help="Maximum iterations")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--resume", help="Resume task by ID")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress.md tracking")
    parser.add_argument("--no-web", action="store_true", help="Disable web tools")
    parser.add_argument("--no-notebooks", action="store_true", help="Disable notebook tools")

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
        enable_web=not args.no_web,
        enable_notebooks=not args.no_notebooks,
    )

    try:
        agent = UltimateSWEAgent(config)
        
        if args.resume:
            result = agent.execute_task("", resume_task_id=args.resume)
        else:
            if args.task:
                task = " ".join(args.task)
            else:
                task = input("Enter comprehensive task: ").strip()

            if not task:
                print("❌ No task provided")
                return

            result = agent.execute_task(task)

        print(f"\n📊 Ultimate Agent Final Summary:")
        print(f"✅ Status: {'Success' if result['success'] else 'Failed'}")
        print(f"🔄 Iterations: {result['iterations']}")
        print(f"🆔 Task ID: {result['task_id']}")
        print(f"🔧 Tools Used: {result.get('tools_used', len(agent.tools))}")
        
        if result.get('files_created'):
            print(f"📁 Files Created/Modified: {result['files_created']}")
        if result.get('sub_agents_spawned'):
            print(f"🤖 Sub-Agents Spawned: {result['sub_agents_spawned']}")
        
        if config.progress_tracking:
            print(f"📋 Comprehensive progress report: {config.progress_file}")

        if not result["success"] and result.get("resume_possible"):
            print(f"💾 Task can be resumed with: --resume {result['task_id']}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted - comprehensive state and progress saved")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
