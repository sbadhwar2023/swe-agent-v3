#!/usr/bin/env python3
"""
Test the working SWE agent
"""

import sys
import os
from pathlib import Path

from swe_agent import SWEAgent, Config


def test_simple_task():
    """Test with a simple software engineering task"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        print("Example: export ANTHROPIC_API_KEY='your_key_here'")
        return False

    config = Config(api_key=api_key, working_dir=".", max_iterations=8, debug_mode=True)

    try:
        agent = SWEAgent(config)

        # Simple Flask app task
        task = "Create a simple Flask hello world app in a file called app.py"

        result = agent.execute_task(task)

        print(f"\n🎯 Test Result: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")

        # Check if file was created
        if os.path.exists("app.py"):
            print("✅ app.py file created")
            with open("app.py", "r") as f:
                content = f.read()
                if "Flask" in content and "hello" in content.lower():
                    print("✅ File contains Flask and hello content")
                else:
                    print("❌ File missing expected content")
        else:
            print("❌ app.py file not created")

        return result["success"]

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing SWE Agent V3\n")
    success = test_simple_task()

    if success:
        print("\n🎉 SWE Agent is working!")
        print("\nYou can now use it with:")
        print("python src/swe_agent.py 'your task here'")
    else:
        print("\n💥 SWE Agent needs fixes")

    sys.exit(0 if success else 1)
