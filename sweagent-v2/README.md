# SWE Agent V2 - Claude Code Equivalent

A complete, fast, intelligent software engineering agent with full Claude Code capabilities.

## Features

### 🔧 Complete Tool Suite
- **File Operations**: `read_file`, `write_file`, `edit_file`, `multi_edit`
- **Search & Analysis**: `glob_files`, `ls_directory`, `grep_search`  
- **Code Execution**: `bash_command`
- **Task Management**: `todo_write`, `task_agent` (spawns real sub-agents)

### 🧠 Intelligence
- **No over-decomposition** - Direct tool usage like Claude Code
- **Real sub-agents** - Spawn specialized agents for complex searches/analysis
- **Intelligent completion detection** - Knows when tasks are done
- **Systematic execution** - Plans complex tasks with todos

### ⚡ Performance
- **Fast execution** - No unnecessary workflow overhead
- **Direct tool calling** - Like Claude Code's approach
- **Parallel sub-agents** - Delegate complex work efficiently

## Quick Start

### Installation
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

### Usage

#### Simple Tasks
```bash
python src/sweagent_v2.py "list all Python files"
python src/sweagent_v2.py "create a hello world script" 
python src/sweagent_v2.py "find TODO comments in the codebase"
```

#### Complex Tasks  
```bash
python src/sweagent_v2.py "create a Flask web application with authentication"
python src/sweagent_v2.py "analyze the codebase and suggest improvements"
python src/sweagent_v2.py "refactor the user management module"
```

#### With Options
```bash
python src/sweagent_v2.py --working-dir /path/to/project --debug "build the project"
python src/sweagent_v2.py --max-iterations 30 "complex multi-step task"
```

## Tool Capabilities

### File Operations
- **read_file**: Read with line ranges, encoding handling
- **write_file**: Create files with directory creation
- **edit_file**: Precise string replacement with undo capability
- **multi_edit**: Atomic batch edits

### Search & Analysis  
- **glob_files**: Advanced pattern matching with time sorting
- **ls_directory**: Directory listing with filtering and metadata
- **grep_search**: Regex search with context lines and file filtering

### Code Execution
- **bash_command**: Shell execution with timeout and error handling

### Task Management
- **todo_write**: Real task tracking with state management
- **task_agent**: Spawn specialized sub-agents for:
  - `search`: File and content searching
  - `analysis`: Code analysis and review  
  - `modification`: Code editing and refactoring
  - `creation`: New file and project creation

## Examples

### Basic File Operations
```bash
# Read a specific file
python src/sweagent_v2.py "read the main.py file"

# Create a new module
python src/sweagent_v2.py "create a user authentication module"

# Search for patterns
python src/sweagent_v2.py "find all functions that use database connections"
```

### Complex Project Tasks
```bash
# Full project creation
python src/sweagent_v2.py "create a REST API with FastAPI including user auth, database models, and tests"

# Code analysis
python src/sweagent_v2.py "analyze this codebase for security vulnerabilities and performance issues"

# Refactoring
python src/sweagent_v2.py "refactor the payment processing code to use the strategy pattern"
```

### Sub-agent Delegation  
```bash
# The agent automatically spawns sub-agents for complex searches:
python src/sweagent_v2.py "find all places where user data is processed and ensure GDPR compliance"
# ^ This will spawn 'search' and 'analysis' sub-agents automatically
```

## Architecture

### Main Agent
- **Intelligent task analysis** - Understands what needs to be done
- **Tool selection** - Chooses right tools for the job
- **Sub-agent management** - Delegates complex work when appropriate
- **Progress tracking** - Uses todos for complex multi-step tasks

### Sub-agents
- **Specialized** - Each type optimized for specific work
- **Autonomous** - Can use tools independently  
- **Reporting** - Return detailed results to main agent
- **Tool access** - Full access to file operations, search, execution

### Key Differences from Complex Workflows
- **No over-engineering** - Direct tool usage when appropriate
- **Intelligent delegation** - Sub-agents for complexity, not everything
- **Fast execution** - No unnecessary planning phases for simple tasks
- **Real completion detection** - Knows when work is actually done

## CLI Options

```
python src/sweagent_v2.py [OPTIONS] TASK

Options:
  --working-dir PATH        Working directory (default: current)
  --max-iterations N        Maximum iterations (default: 20)
  --debug                   Enable debug output
  --non-interactive         Disable interactive mode
  --help                    Show help message
```

## Comparison with Claude Code

| Feature | SWE Agent V2 | Claude Code |
|---------|--------------|-------------|
| File Operations | ✅ Complete | ✅ Complete |
| Search & Analysis | ✅ Complete | ✅ Complete |
| Code Execution | ✅ Complete | ✅ Complete |
| Task Management | ✅ With sub-agents | ✅ Native |
| Speed | ✅ Fast | ✅ Fast |
| Intelligence | ✅ LLM-driven | ✅ LLM-driven |
| Sub-agents | ✅ Real spawning | ✅ Task tool |

## License

MIT License