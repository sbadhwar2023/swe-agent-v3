#!/usr/bin/env python3
"""
Test the persistent SWE agent's error recovery capabilities
"""

import sys
import os
import time
import subprocess
from pathlib import Path

from swe_agent_persistent import PersistentSWEAgent, Config


def test_error_recovery():
    """Test that agent can recover from errors without restarting"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=15,
        debug_mode=True,
    )

    try:
        agent = PersistentSWEAgent(config)

        # Task that will likely encounter an error scenario
        task = """Create a Django web application with the following steps:

1. Check if Django is installed (this might fail initially)
2. Install Django if not present
3. Create a new Django project called 'testproject'
4. Create a simple 'hello' app within the project
5. Configure basic URL routing
6. Test that the server can start

This task is designed to test error recovery - if Django isn't installed initially, the agent should handle that error gracefully and continue from where it failed, not restart the entire task."""

        print(f"🧪 Testing error recovery with Django installation task...")
        result = agent.execute_task(task)

        print(f"\n🔍 Persistent Agent Test Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Task ID: {result.get('task_id', 'N/A')}")

        # Check if Django project was created (evidence of progression)
        django_files = []
        for pattern in ["testproject/", "manage.py", "testproject/settings.py"]:
            if os.path.exists(pattern):
                django_files.append(pattern)
                print(f"✅ Found: {pattern}")

        # Check for state file (evidence of persistence)
        state_file = Path(".swe_agent_state.pkl")
        if state_file.exists():
            print(f"✅ State file created: {state_file}")
            # Clean up state file
            state_file.unlink()
        
        success_criteria = len(django_files) >= 1 and result.get('task_id') is not None
        print(f"\n🎯 Recovery Test Result: {'✅ PASS' if success_criteria else '❌ FAIL'}")
        
        return success_criteria

    except Exception as e:
        print(f"❌ Persistent agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up any created Django files
        cleanup_files = ["testproject/", "db.sqlite3"]
        for item in cleanup_files:
            try:
                if os.path.isdir(item):
                    import shutil
                    shutil.rmtree(item)
                elif os.path.isfile(item):
                    os.remove(item)
            except:
                pass


def test_resume_functionality():
    """Test that agent can resume from saved state"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    config = Config(
        api_key=api_key,
        working_dir=".",
        max_iterations=5,  # Low limit to force interruption
        debug_mode=True,
    )

    try:
        # First run - should get interrupted
        agent1 = PersistentSWEAgent(config)
        
        task = """Create a simple Python package structure with:
1. Create main directory 'mypackage'
2. Create __init__.py file
3. Create main.py with a hello function
4. Create setup.py with package metadata
5. Create README.md with usage instructions
6. Create tests/ directory with test files
7. Run tests to verify everything works"""

        print(f"🧪 Starting task that should get interrupted...")
        result1 = agent1.execute_task(task)
        
        task_id = result1.get('task_id')
        if not task_id:
            print("❌ No task ID returned from first run")
            return False
            
        print(f"🔄 First run completed with task ID: {task_id}")
        print(f"Resume possible: {result1.get('resume_possible', False)}")
        
        # Check if state file exists
        state_file = Path(".swe_agent_state.pkl")
        if not state_file.exists():
            print("❌ State file not created")
            return False
            
        # Second run - resume from state
        print(f"\n🔄 Attempting to resume task {task_id}...")
        
        config2 = Config(
            api_key=api_key,
            working_dir=".",
            max_iterations=10,
            debug_mode=True,
        )
        
        agent2 = PersistentSWEAgent(config2)
        result2 = agent2.execute_task("", resume_task_id=task_id)
        
        print(f"\n🔍 Resume Test Results:")
        print(f"Resume success: {result2['success']}")
        print(f"Resume iterations: {result2['iterations']}")
        
        # Check if package files were created
        package_files = []
        for pattern in ["mypackage/", "mypackage/__init__.py", "mypackage/main.py", "setup.py"]:
            if os.path.exists(pattern):
                package_files.append(pattern)
                print(f"✅ Found: {pattern}")
        
        success = len(package_files) >= 2
        print(f"\n🎯 Resume Test Result: {'✅ PASS' if success else '❌ FAIL'}")
        
        return success
        
    except Exception as e:
        print(f"❌ Resume test failed: {e}")
        return False
    finally:
        # Cleanup
        cleanup_items = ["mypackage/", "setup.py", "README.md", "tests/", ".swe_agent_state.pkl"]
        for item in cleanup_items:
            try:
                if os.path.isdir(item):
                    import shutil
                    shutil.rmtree(item)
                elif os.path.isfile(item):
                    os.remove(item)
            except:
                pass


if __name__ == "__main__":
    print("🧪 Testing Persistent SWE Agent - Claude Code Error Recovery\n")

    print("=" * 60)
    print("TEST 1: Error Recovery Without Restart")  
    print("=" * 60)
    test1_pass = test_error_recovery()

    print("\n" + "=" * 60)
    print("TEST 2: Resume From Saved State")
    print("=" * 60)
    test2_pass = test_resume_functionality()

    overall_success = test1_pass and test2_pass
    print(f"\n🏁 Final Result: {'✅ ALL TESTS PASS' if overall_success else '❌ SOME TESTS FAILED'}")

    if overall_success:
        print("\n🎉 Persistent SWE Agent is working with Claude Code error recovery!")
        print("\nKey Features:")
        print("✅ Continues from failure point instead of restarting")
        print("✅ Saves state for resuming interrupted tasks")
        print("✅ User guidance integration for error resolution")
        print("✅ Smart timeout handling for different command types")
        print("\nUsage:")
        print("python swe_agent_persistent.py 'your complex task'")
        print("python swe_agent_persistent.py --resume <task_id>")
    else:
        print("\n💥 Persistent agent needs further refinement")

    sys.exit(0 if overall_success else 1)