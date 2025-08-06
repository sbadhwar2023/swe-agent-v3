import uuid
import time
import os
import glob
import re
import json
import subprocess
import requests
from typing import Dict, List, Tuple, Optional, Any, Callable, TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from pathlib import Path
import logging
import anthropic
from dataclasses import dataclass

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
try:
    from langgraph_checkpoint.sqlite import SqliteSaver
except ImportError:
    # Fallback for newer versions
    SqliteSaver = None
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

# Set up logging
logging.basicConfig(level=logging.INFO)
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

@dataclass
class SubTask:
    """Represents a decomposed subtask"""
    id: str
    description: str
    tools_needed: List[str]
    expected_output: str
    verification_criteria: str
    priority: int = 1
    status: str = "pending"  # pending, in_progress, completed, failed

# LangChain Tools Definition
@tool
def file_search_tool(pattern: str, directory: str = ".") -> List[str]:
    """Search for files matching a pattern in a directory"""
    try:
        search_pattern = os.path.join(directory, "**", pattern)
        files = glob.glob(search_pattern, recursive=True)
        return files
    except Exception as e:
        return [f"Error: {str(e)}"]

@tool
def grep_search_tool(pattern: str, file_path: str) -> List[Dict[str, Any]]:
    """Search for text patterns in a file"""
    try:
        matches = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append({
                        'line_number': line_num,
                        'line': line.strip(),
                        'file': file_path
                    })
        return matches
    except Exception as e:
        return [{"error": str(e)}]

@tool
def code_analysis_tool(file_path: str) -> Dict[str, Any]:
    """Analyze code file for metrics and complexity"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*')))
        code_lines = total_lines - blank_lines - comment_lines
        
        # Count functions/methods
        function_pattern = r'def\s+\w+|function\s+\w+|class\s+\w+'
        functions = len(re.findall(function_pattern, content, re.IGNORECASE))
        
        return {
            'file': file_path,
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'functions': functions,
            'complexity_score': code_lines / max(functions, 1)
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def file_writer_tool(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file"""
    try:
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Verify file was written
        if os.path.exists(file_path):
            return {
                'file': file_path,
                'size': len(content),
                'lines': content.count('\n') + 1,
                'status': 'success',
                'directory_created': dir_path if dir_path and not os.path.exists(dir_path) else None
            }
        else:
            return {"error": f"File {file_path} was not created successfully"}
            
    except PermissionError:
        return {"error": f"Permission denied writing to {file_path}"}
    except OSError as e:
        return {"error": f"OS error writing file {file_path}: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error writing {file_path}: {str(e)}"}

@tool
def web_request_tool(url: str, method: str = "GET") -> Dict[str, Any]:
    """Make HTTP requests to check web endpoints"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content_length': len(response.content),
            'url': response.url,
            'success': response.status_code < 400
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def file_read_tool(file_path: str, offset: int = 0, limit: int = -1) -> Dict[str, Any]:
    """Read file contents with optional line range"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]
            
        return {
            'file': file_path,
            'content': ''.join(lines),
            'lines_read': len(lines),
            'total_lines': len(open(file_path, 'r').readlines()) if limit == -1 else 'partial',
            'success': True
        }
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except PermissionError:
        return {"error": f"Permission denied: {file_path}"}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}

@tool
def file_edit_tool(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
    """Edit file by replacing old_string with new_string"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_string not in content:
            return {"error": f"String not found in file: {old_string[:50]}..."}
        
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            'file': file_path,
            'replacements': replacements,
            'old_length': len(content),
            'new_length': len(new_content),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error editing file: {str(e)}"}

@tool
def directory_list_tool(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """List directory contents"""
    try:
        items = []
        for item in os.listdir(path):
            if not show_hidden and item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            items.append({
                'name': item,
                'type': 'directory' if is_dir else 'file',
                'size': size,
                'path': item_path
            })
        
        return {
            'path': path,
            'items': sorted(items, key=lambda x: (x['type'], x['name'])),
            'total_items': len(items),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error listing directory: {str(e)}"}

@tool 
def multi_edit_tool(file_path: str, edits: List[Dict[str, str]]) -> Dict[str, Any]:
    """Apply multiple edits to a file in sequence"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        total_edits = 0
        for edit in edits:
            old_str = edit['old_string']
            new_str = edit['new_string']
            replace_all = edit.get('replace_all', False)
            
            if old_str in content:
                if replace_all:
                    content = content.replace(old_str, new_str)
                    total_edits += content.count(old_str)
                else:
                    content = content.replace(old_str, new_str, 1)
                    total_edits += 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'file': file_path,
            'total_edits': total_edits,
            'edits_applied': len(edits),
            'success': True
        }
    except Exception as e:
        return {"error": f"Error applying multi-edits: {str(e)}"}

@tool
def bash_tool(command: str, working_dir: str = ".", timeout: int = 60) -> Dict[str, Any]:
    """Execute bash commands with better error handling"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=working_dir,
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0,
            'working_dir': working_dir
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command '{command}' timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}

@tool
def system_command_tool(command: str, working_dir: str = ".") -> Dict[str, Any]:
    """Execute safe system commands (deprecated - use bash_tool)"""
    try:
        safe_commands = ['ls', 'dir', 'pwd', 'whoami', 'date', 'git status', 'git log', 'npm list', 'pip list', 'mkdir', 'touch', 'cp', 'mv', 'rm -f', 'chmod', 'python', 'node', 'flask run', 'npm', 'pip', 'pytest', 'flake8', 'black']
        if not any(command.startswith(safe_cmd) for safe_cmd in safe_commands):
            return {"error": f"Command not in whitelist: {command}. Use bash_tool for unrestricted commands"}
        
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=working_dir,
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0,
            'working_dir': working_dir
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command '{command}' timed out after 60 seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}

class LangGraphTaskAgent:
    """LangGraph-based multi-agent task system"""
    
    def __init__(self, anthropic_api_key: str):
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=anthropic_api_key,
            temperature=0
        )
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        
        # Define available tools
        self.tools = [
            file_search_tool,
            file_read_tool,
            file_edit_tool,
            file_writer_tool,
            multi_edit_tool,
            directory_list_tool,
            grep_search_tool, 
            code_analysis_tool,
            web_request_tool,
            bash_tool,
            system_command_tool
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
        Based on the planning analysis, decompose this task into specific, executable subtasks:
        
        Task: {state['task_description']}
        Context: {json.dumps(state['context'], indent=2)}
        
        Available tools: {[tool.name for tool in self.tools]}
        
        For each subtask, provide:
        1. A clear, specific description
        2. Which tools to use (from the available list)
        3. Expected output format
        4. How to verify success
        5. Priority (1-5, where 1 is highest)
        
        Format your response as JSON:
        {{
            "subtasks": [
                {{
                    "id": "unique_id",
                    "description": "specific task description",
                    "tools_needed": ["tool_name1", "tool_name2"],
                    "expected_output": "what should be produced",
                    "verification_criteria": "how to check success",
                    "priority": 1
                }}
            ]
        }}
        
        Make subtasks atomic and executable with the available tools.
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
        print(f"\n🔧 Executing: {current_subtask['description']}")
        
        execution_prompt = f"""
        Execute this specific subtask using the available tools, then verify the results:
        
        Subtask: {current_subtask['description']}
        Tools needed: {current_subtask['tools_needed']}
        Expected output: {current_subtask['expected_output']}
        Verification criteria: {current_subtask['verification_criteria']}
        Context: {json.dumps(state['context'], indent=2)}
        
        IMPORTANT EXECUTION STEPS:
        1. First, check if the task is already completed by examining existing files
        2. Use the tools to complete this subtask only if needed
        3. Test/verify functionality using bash_tool (e.g., run server, test endpoints with curl)
        4. Provide a clear verification assessment stating "COMPLETED" or "FAILED" with reasons
        
        For web applications:
        - Use file_read_tool to check existing implementation
        - Use bash_tool to test functionality (start server, curl requests)
        - Clearly state if functionality already exists and works
        
        Be specific about tool parameters and handle any errors gracefully.
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
                    messages.extend(tool_result["messages"])
            
            # Get final response with verification
            self._throttle_request()
            final_response = self.llm.invoke(messages)
            messages.append(final_response)
            
        except Exception as e:
            print(f"   ⚠️ Execution error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
            final_response = AIMessage(content=f"Task execution encountered an error: {str(e)}")
            messages.append(final_response)
        
        # Store result with better verification
        response_content = final_response.content.lower()
        
        # More intelligent success detection
        success_indicators = ["completed", "success", "created", "implemented", "working", "done"]
        error_indicators = ["error", "failed", "exception", "traceback", "not found", "permission denied"]
        
        has_success = any(indicator in response_content for indicator in success_indicators)
        has_error = any(indicator in response_content for indicator in error_indicators)
        
        # If no clear indicators, assume success unless explicit error
        if not has_success and not has_error:
            success = True
        elif has_success and not has_error:
            success = True
        elif has_error and not has_success:
            success = False
        else:
            # Both present, lean towards success unless severe error
            success = not any(severe in response_content for severe in ["exception", "traceback", "permission denied"])
        
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
        
        messages = state["messages"] + [HumanMessage(content=aggregation_prompt)]
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
        """Execute a task using the LangGraph workflow"""
        
        thread_id = str(uuid.uuid4())
        context = context or {}
        
        initial_state = {
            "messages": [],
            "task_description": task_description,
            "context": context,
            "subtasks": [],
            "current_subtask": None,
            "results": [],
            "final_result": None,
            "iteration_count": 0
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
            return final_state["final_result"]
            
        except Exception as e:
            print(f"\n❌ Task execution failed: {str(e)}")
            logger.error(f"❌ LangGraph task execution failed: {e}")
            return {
                "task_description": task_description,
                "success": False,
                "error": str(e),
                "execution_time": time.time()
            }

# Example usage
if __name__ == "__main__":
    # Initialize with Anthropic API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        exit(1)
    
    # Create LangGraph agent
    agent = LangGraphTaskAgent(api_key)
    
    print("=== LangGraph-Integrated Multi-Agent Task System ===")
    """
    # Example 1: Code analysis task
    print("\n1. Executing code analysis task...")
    result1 = agent.execute_task(
        "Analyze the code quality of Python files in this project and identify areas for improvement",
        context={
            "project_directory": ".",
            "file_types": ["*.py"],
            "analysis_depth": "comprehensive"
        }
    )
    
    print("📊 Code Analysis Results:")
    print(f"Success Rate: {result1.get('success_rate', 0):.1%}")
    print(f"Subtasks: {result1.get('subtasks_completed', 0)}/{result1.get('subtasks_total', 0)}")
    print("Report Preview:", result1.get('final_report', 'No report available')[:200] + "...")
    
    # Example 2: Security audit task
    print("\n2. Executing security audit task...")
    result2 = agent.execute_task(
        "Perform a security audit by scanning for vulnerabilities and generating a security report",
        context={
            "scan_types": ["hardcoded_secrets", "dangerous_functions", "file_permissions"],
            "output_format": "detailed_report"
        }
    )
    
    print("🔒 Security Audit Results:")
    print(f"Success Rate: {result2.get('success_rate', 0):.1%}")
    print(f"Subtasks: {result2.get('subtasks_completed', 0)}/{result2.get('subtasks_total', 0)}")
    print("Report Preview:", result2.get('final_report', 'No report available')[:200] + "...")
    
    # Example 3: Documentation task
    print("\n3. Executing documentation task...")
    result3 = agent.execute_task(
        "Create comprehensive documentation by analyzing code structure and generating README and API docs",
        context={
            "documentation_types": ["README", "API_reference", "usage_examples"],
            "target_audience": "developers"
        }
    )
    """
    
    print ("Test")
    #result4 = agent.execute_task("Create a webapp that takes user input for name, and prints Hello name")
    result4 = agent.execute_task("Can you create a webapp that takes in keywords from user as input, and provides research papers in the order of relevance, save it in folder research.")    

    print("📚 Documentation Results:")
    print(f"Success Rate: {result4.get('success_rate', 0):.1%}")
    print(f"Subtasks: {result4.get('subtasks_completed', 0)}/{result4.get('subtasks_total', 0)}")
    print("Report Preview:", result4.get('final_report', 'No report available')[:200] + "...")
    
    print("\n✅ All LangGraph task executions completed!")
    print("\nThe system used LangGraph's workflow orchestration to:")
    print("- Plan each task strategically")
    print("- Decompose into executable subtasks") 
    print("- Execute with proper tool usage")
    print("- Verify results against criteria")
    print("- Aggregate into comprehensive reports")
