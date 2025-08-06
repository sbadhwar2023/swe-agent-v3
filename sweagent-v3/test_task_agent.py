#!/usr/bin/env python3
"""
Test examples for task_agent functionality
"""

import sys
import os
from pathlib import Path

from swe_agent_interactive import InteractiveSWEAgent, Config


def test_simple_task_agent():
    """Test task_agent with a simple focused task"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=10,
        debug_mode=True,
        interactive_mode=False,  # Non-interactive for testing
    )

    try:
        agent = InteractiveSWEAgent(config)

        # Task that uses task_agent for a specific sub-task
        task = """Create a simple Python calculator. Use task_agent to handle the math operations implementation while you handle the main structure.

Steps:
1. Create the main calculator.py file structure
2. Use task_agent to implement the math functions (add, subtract, multiply, divide)
3. Create a simple test to verify it works"""

        result = agent.execute_task(task)

        print(f"\n🔍 Task Agent Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")

        # Check if files were created
        if os.path.exists("calculator.py"):
            print("✅ calculator.py created")
            with open("calculator.py", "r") as f:
                content = f.read()
                if "def " in content and ("add" in content or "subtract" in content):
                    print("✅ Contains function definitions")
                else:
                    print("❌ Missing expected function definitions")
        else:
            print("❌ calculator.py not found")

        return result["success"]

    except Exception as e:
        print(f"❌ Task agent test failed: {e}")
        return False


def test_analysis_task_agent():
    """Test task_agent for code analysis"""

    # Create a sample file to analyze
    sample_code = """
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n-1)

def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n+1):
        a, b = b, a + b
    return b

print(factorial(5))
print(fibonacci(10))
"""

    with open("sample.py", "w") as f:
        f.write(sample_code)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=8,
        debug_mode=True,
        interactive_mode=False,
    )

    try:
        agent = InteractiveSWEAgent(config)

        # Task that uses task_agent for analysis
        task = """Analyze the sample.py file. Use task_agent to:
1. Find all function definitions in the file
2. Check for any potential issues or improvements
3. Suggest optimizations

Then create a summary report."""

        result = agent.execute_task(task)

        print(f"\n🔍 Analysis Task Agent Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")

        # Clean up
        if os.path.exists("sample.py"):
            os.remove("sample.py")

        return result["success"]

    except Exception as e:
        print(f"❌ Analysis task agent test failed: {e}")
        return False


def test_file_organization_task_agent():
    """Test task_agent for file organization tasks"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=8,
        debug_mode=True,
        interactive_mode=False,
    )

    try:
        agent = InteractiveSWEAgent(config)

        # Task that uses task_agent for organization
        task = """Create a proper Python project structure for a 'utils' package. Use task_agent to:
1. Create the directory structure (utils/, utils/math/, utils/string/, tests/)
2. Create __init__.py files where needed
3. Create sample utility functions in each module

Main agent should coordinate and create a README."""

        result = agent.execute_task(task)

        print(f"\n🔍 Organization Task Agent Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")

        # Check structure
        expected_dirs = ["utils", "tests"]
        found_dirs = []

        for dir_name in expected_dirs:
            if os.path.exists(dir_name):
                found_dirs.append(dir_name)
                print(f"✅ Created {dir_name}/")
            else:
                print(f"❌ Missing {dir_name}/")

        success = result["success"] and len(found_dirs) >= 1
        return success

    except Exception as e:
        print(f"❌ Organization task agent test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Task Agent Functionality\n")

    tests = [
        ("Simple Task Agent", test_simple_task_agent),
        ("Analysis Task Agent", test_analysis_task_agent),
        ("Organization Task Agent", test_file_organization_task_agent),
    ]

    results = []

    for test_name, test_func in tests:
        print("=" * 60)
        print(f"TEST: {test_name}")
        print("=" * 60)

        try:
            success = test_func()
            results.append((test_name, success))
            print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append((test_name, False))

        print()

    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)

    print("=" * 60)
    print("TASK AGENT TEST SUMMARY")
    print("=" * 60)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All task agent tests passed!")
    else:
        print("💥 Some task agent tests failed - needs debugging")

    sys.exit(0 if passed == total else 1)
