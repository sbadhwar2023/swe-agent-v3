"""
Main agent implementation for SWE Agent
"""

import uuid
import time
import json
import signal
import logging
import re
from typing import Dict, List, Optional, Any, TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
try:
    from langgraph_checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic

from .config import UserConfig
from .permissions import PermissionManager
from .todos import TodoManager, SubTask
from .tools import (
    file_search_tool, file_read_tool, directory_list_tool, grep_search_tool,
    code_analysis_tool, web_request_tool, multi_edit_tool, system_command_tool,
    create_permission_aware_bash_tool, create_permission_aware_file_tools,
    todo_write_tool, task_delegation_tool
)

# Set up logging
logger = logging.getLogger(__name__)


# State definition for LangGraph
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    task_description: str
    context: Dict[str, Any]
    subtasks: List[Dict[str, Any]]
    current_subtask: Optional[Dict[str, Any]]
    results: List[Dict[str, Any]]
    final_result: Optional[Dict[str, Any]]
    iteration_count: int
    user_config: Dict[str, Any]
    permission_level: str
    interactive_mode: bool
    paused: bool


class LangGraphTaskAgent:
    """LangGraph-based multi-agent task system with external configuration and permission management"""
    
    def __init__(self, anthropic_api_key: str, config: UserConfig = None):
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=anthropic_api_key,
            temperature=0
        )
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 0.1 seconds between requests (much faster)
        
        # Initialize user configuration
        self.config = config or UserConfig()
        self.permission_manager = PermissionManager(self.config.permission_level)
        self.todo_manager = TodoManager(self.config.show_todo_updates)
        self.paused = False
        self.stop_requested = False
        
        # Setup signal handlers for interruption
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
        
        # Create permission-aware tools
        permission_aware_bash = create_permission_aware_bash_tool(self.permission_manager)
        permission_aware_writer, permission_aware_editor = create_permission_aware_file_tools(self.permission_manager)
        
        # Define available tools
        self.tools = [
            file_search_tool,
            file_read_tool,
            permission_aware_editor,  # Use permission-aware version
            permission_aware_writer,  # Use permission-aware version
            multi_edit_tool,
            directory_list_tool,
            grep_search_tool, 
            code_analysis_tool,
            web_request_tool,
            permission_aware_bash,  # Use permission-aware version
            system_command_tool,
            todo_write_tool,  # NEW: Todo management like Claude Code
            task_delegation_tool  # NEW: Sub-agent delegation
        ]
        
        self.tool_executor = ToolNode(self.tools)
        
        # Create the graph
        self.workflow = self._create_workflow()
        
        # Add memory with SQLite checkpointer
        if SqliteSaver:
            memory = SqliteSaver.from_conn_string(":memory:")
            self.app = self.workflow.compile(checkpointer=memory)
        else:
            # Run without checkpointer for newer versions
            self.app = self.workflow.compile()
    
    def _handle_interrupt(self, signum, frame):
        """Handle user interruption (Ctrl+C)"""
        print(f"\n🛑 Interruption received (signal {signum})")
        
        if self.config.interactive_mode:
            print("\nOptions:")
            print("1. Pause execution (resume later)")
            print("2. Stop execution")
            print("3. Continue execution")
            
            try:
                choice = input("Enter choice (1-3): ").strip()
                if choice == "1":
                    self.paused = True
                    self.todo_manager.update_todo("main_task", "paused", "Execution paused by user")
                    print("⏸️ Execution paused. Use resume_execution() to continue.")
                elif choice == "2":
                    self.stop_requested = True
                    print("🛑 Stop requested. Execution will halt gracefully.")
                elif choice == "3":
                    print("▶️ Continuing execution...")
                else:
                    print("Invalid choice. Continuing execution...")
            except (EOFError, KeyboardInterrupt):
                self.stop_requested = True
                print("\n🛑 Force stop requested.")
        else:
            self.stop_requested = True
            print("🛑 Non-interactive mode: stopping execution.")
    
    def pause_execution(self):
        """Pause execution programmatically"""
        self.paused = True
        self.todo_manager.update_todo("main_task", "paused", "Execution paused programmatically")
        print("⏸️ Execution paused.")
    
    def resume_execution(self):
        """Resume paused execution"""
        self.paused = False
        self.todo_manager.update_todo("main_task", "in_progress", "Execution resumed")
        print("▶️ Execution resumed.")
    
    def stop_execution(self):
        """Stop execution programmatically"""
        self.stop_requested = True
        print("🛑 Stop requested.")
    
    def _wait_if_paused(self):
        """Wait while execution is paused"""
        while self.paused and not self.stop_requested:
            time.sleep(0.5)
        
        if self.stop_requested:
            raise KeyboardInterrupt("Execution stopped by user request")
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("decomposer", self._decomposer_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("aggregator", self._aggregator_node)
        
        # Define edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "decomposer")
        workflow.add_edge("decomposer", "executor")
        workflow.add_conditional_edges(
            "executor",
            self._should_continue,
            {
                "continue": "executor",
                "aggregate": "aggregator"
            }
        )
        workflow.add_edge("aggregator", END)
        
        return workflow
    
    def _throttle_request(self):
        """Throttle API requests to prevent rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            print(f"   ⏱️ Throttling request: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Plan the overall approach for the task"""
        print(f"\n📋 Task: {state['task_description']}")
        print("🔄 Planning phase started...")
        logger.info("🔄 Planning phase started")
        
        planning_prompt = f"""
        Analyze this task and create an execution plan:
        
        Task: {state['task_description']}
        Context: {json.dumps(state['context'], indent=2)}
        
        Available tools: {[tool.name for tool in self.tools]}
        
        Create a high-level execution strategy. Consider:
        1. What information do we need to gather?
        2. What tools will be most useful?
        3. What are the key success criteria?
        4. How should we break this down?
        
        Provide your analysis as a structured plan.
        """
        
        messages = state["messages"] + [HumanMessage(content=planning_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        new_state = state.copy()
        new_state["messages"] = messages + [response]
        
        print("✅ Planning phase completed")
        logger.info("✅ Planning phase completed")
        return new_state
    
    def _decomposer_node(self, state: AgentState) -> AgentState:
        """Decompose the task into specific subtasks"""
        print("🔄 Breaking down into subtasks...")
        logger.info("🔄 Decomposition phase started")
        
        decomposition_prompt = f"""
        You are an intelligent task decomposer. Analyze this task and decide how to execute it most efficiently.

        Task: {state['task_description']}
        Available tools: {[tool.name for tool in self.tools]}

        INTELLIGENCE RULES:
        1. SINGLE TOOL TASKS: If the task can be completed with one tool call, create exactly ONE subtask
        2. MULTI-STEP TASKS: Only create multiple subtasks if genuinely needed for complex operations
        3. NO OVER-ENGINEERING: Don't create verification steps for simple operations

        SINGLE SUBTASK EXAMPLES:
        - "list files" → Use directory_list_tool
        - "find .py files" → Use file_search_tool  
        - "read config.py" → Use file_read_tool
        - "create hello world script" → Use file_writer_tool
        - "show current directory" → Use bash_tool with pwd

        MULTIPLE SUBTASK EXAMPLES:
        - "create Flask web application" → Multiple files + setup + testing
        - "analyze codebase and refactor" → Analysis + modifications + verification
        - "setup development environment" → Install + configure + test

        Be intelligent about tool selection. Match the task complexity to subtask complexity.

        Format as JSON:
        {{
            "subtasks": [
                {{
                    "id": "unique_id",
                    "description": "what to accomplish",
                    "tools_needed": ["appropriate_tool"],
                    "expected_output": "what should be produced", 
                    "verification_criteria": "success criteria",
                    "priority": 1
                }}
            ]
        }}

        Think carefully: Does this task need 1 subtask or multiple? Choose wisely.
        """
        
        messages = state["messages"] + [HumanMessage(content=decomposition_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        # Parse the subtasks
        try:
            subtasks_data = json.loads(response.content)
            subtasks = []
            for task_data in subtasks_data["subtasks"]:
                subtask = SubTask(
                    id=task_data["id"],
                    description=task_data["description"],
                    tools_needed=task_data["tools_needed"],
                    expected_output=task_data["expected_output"],
                    verification_criteria=task_data["verification_criteria"],
                    priority=task_data.get("priority", 3)
                )
                subtasks.append(subtask.__dict__)
            
            # Sort by priority
            subtasks.sort(key=lambda x: x["priority"])
            
        except Exception as e:
            logger.error(f"Failed to parse subtasks: {e}")
            # Fallback single subtask
            subtasks = [{
                "id": "fallback_task",
                "description": state['task_description'],
                "tools_needed": ["file_search_tool"],
                "expected_output": "Task completion",
                "verification_criteria": "Task executed without errors",
                "priority": 1,
                "status": "pending"
            }]
        
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [response]
        new_state["subtasks"] = subtasks
        new_state["results"] = []
        new_state["iteration_count"] = 0
        
        print(f"✅ Created {len(subtasks)} subtasks:")
        for i, task in enumerate(subtasks, 1):
            print(f"   {i}. {task['description'][:60]}{'...' if len(task['description']) > 60 else ''}")
        logger.info(f"✅ Decomposed into {len(subtasks)} subtasks")
        return new_state
    
    def _executor_node(self, state: AgentState) -> AgentState:
        """Execute and verify the current subtask in a single API call"""
        self._wait_if_paused()  # Check if paused
        logger.info("🔄 Execution phase started")
        
        # Get next pending subtask
        current_subtask = None
        for subtask in state["subtasks"]:
            if subtask["status"] == "pending":
                current_subtask = subtask
                break
        
        if not current_subtask:
            logger.info("No more subtasks to execute")
            new_state = state.copy()
            return new_state
        
        current_subtask["status"] = "in_progress"
        
        # Update todo manager
        self.todo_manager.update_todo(
            current_subtask["id"], 
            "in_progress", 
            current_subtask["description"]
        )
        
        print(f"\n🔧 Executing: {current_subtask['description']}")
        
        execution_prompt = f"""
        Execute this specific subtask using the available tools. DO NOT just check if files exist - actually create/modify what is needed:
        
        Subtask: {current_subtask['description']}
        Tools needed: {current_subtask['tools_needed']}
        Expected output: {current_subtask['expected_output']}
        Verification criteria: {current_subtask['verification_criteria']}
        Context: {json.dumps(state['context'], indent=2)}
        
        IMPORTANT EXECUTION STEPS:
        1. ACTUALLY DO THE WORK - create files, install packages, etc. using the appropriate tools
        2. Use file_writer_tool to create new files, not just file_read_tool to check them
        3. Use bash_tool for installations, running commands, testing functionality
        4. Only mark as COMPLETED if you actually created/modified something concrete
        5. Provide specific evidence of what was created/done
        
        For file creation tasks:
        - Use file_writer_tool with the actual file content
        - Use directory_list_tool to verify files were created
        
        For installations:
        - Use bash_tool to run pip install, npm install, etc.
        
        Be specific about tool parameters and provide concrete outputs showing what was accomplished.
        """
        
        messages = state["messages"] + [HumanMessage(content=execution_prompt)]
        
        # Execute with tool calling
        try:
            self._throttle_request()
            response = self.llm.bind_tools(self.tools).invoke(messages)
            messages.append(response)
            
            # Execute any tool calls
            if response.tool_calls:
                print(f"   🔧 Using tools: {[call['name'] for call in response.tool_calls]}")
                tool_result = self.tool_executor.invoke({"messages": [response]})
                if "messages" in tool_result:
                    # Add all tool result messages immediately after the tool use message
                    for tool_msg in tool_result["messages"]:
                        messages.append(tool_msg)
            
            # Get final response with verification
            self._throttle_request()
            final_response = self.llm.invoke(messages)
            messages.append(final_response)
            
        except Exception as e:
            print(f"   ⚠️ Execution error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
            final_response = AIMessage(content=f"Task execution encountered an error: {str(e)}")
            messages.append(final_response)
        
        # Store result with better verification
        response_content = str(final_response.content).lower() if final_response.content else ""
        
        # Success detection for both creation and read operations
        concrete_success_indicators = [
            # Creation/modification indicators
            "file created", "successfully created", "successfully written",
            "installed successfully", "server started", "directory created",
            "successfully executed", "file written", "command completed",
            # Read/search indicators
            "found", "located", "search completed", "files found", "results returned",
            "listed", "displayed", "retrieved", "analyzed", "completed successfully",
            "operation successful", "task completed", "finished"
        ]
        error_indicators = ["error", "failed", "exception", "traceback", "not found", "permission denied"]
        
        # Check if actual tool results show success
        tool_success = False
        if response.tool_calls:  # Check if tools were called
            # If tools were called, check their results in the messages
            for msg in messages[-5:]:  # Check recent messages for tool results
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    msg_content = str(msg.content).lower()
                    # Look for success indicators in tool results
                    success_patterns = ["success", "created", "written", "installed", "found", "located", "listed", "total_items"]
                    if any(pattern in msg_content for pattern in success_patterns):
                        if "error" not in msg_content and "failed" not in msg_content:
                            tool_success = True
                            break
        
        has_concrete_success = any(indicator in response_content for indicator in concrete_success_indicators)
        has_error = any(indicator in response_content for indicator in error_indicators)
        
        # Require concrete evidence of work done
        success = (has_concrete_success or tool_success) and not has_error
        
        result = {
            "subtask_id": current_subtask["id"],
            "subtask_description": current_subtask["description"],
            "execution_messages": [msg.content for msg in messages[-3:]],
            "success": success,
            "output": final_response.content,
            "verified": True
        }
        
        current_subtask["status"] = "completed" if result["success"] else "failed"
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} Task {'completed' if result['success'] else 'failed'}: {current_subtask['description'][:50]}{'...' if len(current_subtask['description']) > 50 else ''}")
        
        # Update todo manager
        self.todo_manager.update_todo(
            current_subtask["id"], 
            "completed" if result["success"] else "failed", 
            current_subtask["description"]
        )
        
        new_state = state.copy()
        new_state["messages"] = messages
        new_state["current_subtask"] = current_subtask
        new_state["results"].append(result)
        new_state["iteration_count"] += 1
        
        logger.info(f"✅ Executed subtask: {current_subtask['description'][:50]}...")
        return new_state
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue executing subtasks or aggregate results"""
        pending_subtasks = [s for s in state["subtasks"] if s["status"] == "pending"]
        
        if pending_subtasks and state["iteration_count"] < 10:  # Max 10 iterations
            return "continue"
        else:
            return "aggregate"
    
    def _aggregator_node(self, state: AgentState) -> AgentState:
        """Aggregate all results into a final report"""
        completed = len([s for s in state['subtasks'] if s['status'] == 'completed'])
        failed = len([s for s in state['subtasks'] if s['status'] == 'failed'])
        total = len(state['subtasks'])
        
        print(f"\n📊 Task Summary: {completed}/{total} completed, {failed} failed")
        print("📝 Generating final report...")
        logger.info("🔄 Aggregation phase started")
        
        aggregation_prompt = f"""
        Create a comprehensive final report based on all subtask results:
        
        Original Task: {state['task_description']}
        
        Subtasks Completed: {len([s for s in state['subtasks'] if s['status'] == 'completed'])}
        Total Subtasks: {len(state['subtasks'])}
        
        Results Summary:
        {json.dumps(state['results'], indent=2)}
        
        Provide a comprehensive report including:
        1. Executive summary
        2. Key findings
        3. Detailed results for each subtask
        4. Overall success assessment
        5. Recommendations for next steps
        
        Format the report in a clear, structured manner.
        """
        
        # Filter messages carefully to maintain tool_use/tool_result pairing
        valid_messages = []
        for i, msg in enumerate(state["messages"]):
            # Always include tool messages to maintain pairing
            if hasattr(msg, 'type') and msg.type in ['tool', 'tool_result']:
                valid_messages.append(msg)
            # Include messages with actual content
            elif hasattr(msg, 'content') and msg.content and str(msg.content).strip():
                valid_messages.append(msg)
            # Include AI messages with tool calls even if content is empty
            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                valid_messages.append(msg)
        
        messages = valid_messages + [HumanMessage(content=aggregation_prompt)]
        self._throttle_request()
        response = self.llm.invoke(messages)
        
        # Create final result
        final_result = {
            "task_description": state["task_description"],
            "subtasks_total": len(state["subtasks"]),
            "subtasks_completed": len([s for s in state["subtasks"] if s["status"] == "completed"]),
            "subtasks_failed": len([s for s in state["subtasks"] if s["status"] == "failed"]),
            "success_rate": len([r for r in state["results"] if r["success"]]) / max(len(state["results"]), 1),
            "detailed_results": state["results"],
            "final_report": response.content,
            "execution_time": time.time()
        }
        
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [response]
        new_state["final_result"] = final_result
        
        print("✅ Final report generated")
        logger.info("✅ Final aggregation completed")
        return new_state
    

    def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using the intelligent LangGraph workflow"""
        return self.execute_task_full(task_description, context)

    def execute_task_full(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using the full LangGraph workflow"""
        thread_id = str(uuid.uuid4())
        context = context or {}
        
        # Add main task to todo manager
        self.todo_manager.update_todo("main_task", "in_progress", task_description)
        
        initial_state = {
            "messages": [],
            "task_description": task_description,
            "context": context,
            "subtasks": [],
            "current_subtask": None,
            "results": [],
            "final_result": None,
            "iteration_count": 0,
            "user_config": self.config.__dict__,
            "permission_level": self.config.permission_level,
            "interactive_mode": self.config.interactive_mode,
            "paused": self.paused
        }
        
        print(f"\n🚀 Starting task execution...")
        logger.info(f"🚀 Starting LangGraph task execution: {task_description}")
        
        try:
            # Execute the workflow
            final_state = self.app.invoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}}
            )
            
            print("\n🎉 Task execution completed successfully!")
            logger.info("✅ LangGraph task execution completed successfully")
            
            # Update main task as completed
            self.todo_manager.update_todo("main_task", "completed", task_description)
            
            # Show final todo summary if configured
            if self.config.show_todo_updates:
                summary = self.todo_manager.get_status_summary()
                print(f"\n📊 Final Todo Summary: {summary}")
            
            return final_state["final_result"]
            
        except KeyboardInterrupt:
            print(f"\n⏸️ Task execution interrupted by user")
            self.todo_manager.update_todo("main_task", "paused", f"Task interrupted: {task_description}")
            return {
                "task_description": task_description,
                "success": False,
                "interrupted": True,
                "execution_time": time.time()
            }
        except Exception as e:
            print(f"\n❌ Task execution failed: {str(e)}")
            logger.error(f"❌ LangGraph task execution failed: {e}")
            self.todo_manager.update_todo("main_task", "failed", f"Task failed: {task_description}")
            return {
                "task_description": task_description,
                "success": False,
                "error": str(e),
                "execution_time": time.time()
            }