#!/usr/bin/env python3
"""
Test the enhanced SWE agent with complex tasks
"""

import sys
import os
from pathlib import Path

from swe_agent_enhanced import EnhancedSWEAgent, Config


def test_complex_project():
    """Test with a complex multi-step software project"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=25,
        debug_mode=True,
        enable_web=False,  # Disable web for testing
    )

    try:
        agent = EnhancedSWEAgent(config)

        # Complex task that requires multiple tools and planning
        task = """Create a complete Python project for a task management CLI tool with the following requirements:

1. Project structure with proper directories (src/, tests/, docs/)
2. A main CLI script that can add, list, and complete tasks
3. Task storage in JSON format
4. Unit tests for all functionality
5. A README with installation and usage instructions
6. Requirements.txt with dependencies
7. Use argparse for CLI interface
8. Add proper error handling and logging

Use your full tool suite: start with todo_write to plan, use glob_search and grep_search to understand any existing code, and create a professional project structure."""

        result = agent.execute_task(task)

        print(f"\n🔍 Enhanced Agent Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")

        # Check if project structure was created
        expected_files = ["src/", "tests/", "README.md", "requirements.txt"]

        found_items = []
        for item in expected_files:
            if os.path.exists(item):
                found_items.append(item)
                print(f"✅ Created {item}")
            else:
                print(f"❌ Missing {item}")

        # Check for Python files
        python_files = list(Path(".").rglob("*.py"))
        print(f"📄 Python files created: {len(python_files)}")
        for py_file in python_files[:5]:  # Show first 5
            print(f"   - {py_file}")

        success = result["success"] and len(found_items) >= 2 and len(python_files) >= 2
        print(f"\n🎯 Overall Test Result: {'✅ PASS' if success else '❌ FAIL'}")

        return success

    except Exception as e:
        print(f"❌ Enhanced agent test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_code_analysis():
    """Test code analysis capabilities"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    # Create a sample Python file to analyze
    sample_code = """
def calculate_factorial(n):
    if n < 0:
        return None
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
"""

    with open("sample_code.py", "w") as f:
        f.write(sample_code)

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=15,
        debug_mode=True,
        enable_web=False,
    )

    try:
        agent = EnhancedSWEAgent(config)

        # Analysis task using multiple search tools
        task = """Analyze the sample_code.py file using your search and analysis tools:

1. Use grep_search to find all function definitions
2. Use grep_search to find any potential issues (like recursion without optimization)
3. Use task_agent to spawn an analysis sub-agent to review the code quality
4. Suggest improvements and create an improved version of the file
5. Use todo_write to track your analysis steps

Show the power of your enhanced tool suite!"""

        result = agent.execute_task(task)

        print(f"\n🔍 Code Analysis Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")

        # Clean up
        if os.path.exists("sample_code.py"):
            os.remove("sample_code.py")

        return result["success"]

    except Exception as e:
        print(f"❌ Code analysis test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Enhanced SWE Agent V3\n")

    print("=" * 60)
    print("TEST 1: Complex Project Creation")
    print("=" * 60)
    test1_pass = test_complex_project()

    print("\n" + "=" * 60)
    print("TEST 2: Code Analysis Capabilities")
    print("=" * 60)
    test2_pass = test_code_analysis()

    overall_success = test1_pass and test2_pass
    print(
        f"\n🏁 Final Result: {'✅ ALL TESTS PASS' if overall_success else '❌ SOME TESTS FAILED'}"
    )

    if overall_success:
        print("\n🎉 Enhanced SWE Agent is working with full Claude Code capabilities!")
        print("\nYou can now use it with:")
        print("python swe_agent_enhanced.py 'complex software engineering task'")
    else:
        print("\n💥 Enhanced agent needs further refinement")

    sys.exit(0 if overall_success else 1)
