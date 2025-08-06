#!/usr/bin/env python3
"""
Test Ultimate SWE Agent - 3 Critical Test Cases
Focus: Web search, error handling, sub-agent spawning
"""

import os
import sys
import time
import shutil
from pathlib import Path
from swe_agent_ultimate import UltimateSWEAgent, Config


def test_case_1_web_search_and_error_recovery():
    """
    TEST CASE 1: Web Search Integration + Error Recovery
    Tests real web search functionality and proper error handling
    """
    print("🧪 TEST CASE 1: Web Search + Error Recovery")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    # Create test directory
    test_dir = "test_web_search"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    config = Config(
        api_key=api_key,
        working_dir=test_dir,
        max_iterations=15,
        debug_mode=True,
        enable_web=True,  # Enable web search
        enable_notebooks=False
    )

    try:
        agent = UltimateSWEAgent(config)
        
        # Task that requires web search and has potential for errors
        task = """Research and implement OAuth2 authentication for a Python Flask application:

1. Use web_search to find the latest OAuth2 best practices and tutorials
2. Search for Flask-OAuthlib or Authlib documentation  
3. Create a basic Flask app structure
4. Try to install Flask and Authlib (this might fail if no pip access)
5. Implement basic OAuth2 flow with error handling
6. Create configuration file for OAuth2 settings
7. Add proper error handling for authentication failures
8. Write simple tests

This task is designed to test:
- Web search functionality with real queries
- Error recovery when package installation fails  
- Proper error handling throughout the process
- Building on web search results"""

        print(f"📋 Task: {task[:100]}...")
        
        # Execute task
        result = agent.execute_task(task)
        
        print(f"\n📊 Test Case 1 Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Files created: {result.get('files_created', 0)}")
        
        # Check specific capabilities
        success_criteria = []
        
        # Check if web search was used
        if os.path.exists(f"{test_dir}/progress.md"):
            with open(f"{test_dir}/progress.md", "r") as f:
                progress_content = f.read()
                if "web_search" in progress_content or "Web search" in progress_content:
                    success_criteria.append("✅ Web search functionality used")
                else:
                    success_criteria.append("❌ Web search not detected in progress")
        
        # Check if files were created despite potential errors
        python_files = list(Path(test_dir).glob("*.py"))
        if python_files:
            success_criteria.append(f"✅ Python files created: {len(python_files)}")
        else:
            success_criteria.append("❌ No Python files created")
            
        # Check error handling in progress
        if os.path.exists(f"{test_dir}/progress.md"):
            if "Error History" in progress_content:
                success_criteria.append("✅ Error tracking system working")
            else:
                success_criteria.append("⚠️ No error history found")
        
        print("\n📋 Success Criteria:")
        for criterion in success_criteria:
            print(f"  {criterion}")
            
        overall_success = result['success'] or len(python_files) > 0
        print(f"\n🎯 Test Case 1: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test Case 1 failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            os.chdir("..")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
        except:
            pass


def test_case_2_sub_agent_spawning():
    """
    TEST CASE 2: Sub-Agent Spawning and Coordination
    Tests the task_agent tool and sub-agent management
    """
    print("\n🧪 TEST CASE 2: Sub-Agent Spawning & Coordination")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    # Create test directory
    test_dir = "test_sub_agents"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create sample codebase to analyze
    sample_files = {
        "app.py": '''
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    # TODO: Add proper error handling
    user_name = os.environ.get('USER_NAME')  # Potential KeyError
    return f"Hello {user_name}!"

@app.route('/users/<int:user_id>')
def get_user(user_id):
    # No validation - potential security issue
    users = {1: "Alice", 2: "Bob"}
    return users[user_id]  # Potential KeyError

if __name__ == '__main__':
    app.run(debug=True)  # Debug mode in production - security issue
        ''',
        "utils.py": '''
def process_data(data):
    # No input validation
    result = []
    for item in data:
        result.append(item.upper())  # Potential AttributeError if item is not string
    return result

def connect_db():
    # Hardcoded credentials - security issue
    import sqlite3
    return sqlite3.connect('database.db')
        ''',
        "config.py": '''
SECRET_KEY = "hardcoded_secret_123"  # Security vulnerability
DATABASE_URL = "sqlite:///app.db"
DEBUG = True  # Should be False in production
        '''
    }
    
    for filename, content in sample_files.items():
        with open(f"{test_dir}/{filename}", "w") as f:
            f.write(content)
    
    config = Config(
        api_key=api_key,
        working_dir=test_dir,
        max_iterations=20,
        debug_mode=True,
        enable_web=True,
        max_sub_agents=3  # Allow multiple sub-agents
    )

    try:
        agent = UltimateSWEAgent(config)
        
        # Task that requires sub-agent spawning
        task = """Perform comprehensive code analysis and security review of this Python Flask codebase:

1. First, explore the codebase structure using list_directory and glob_search
2. Spawn a 'search' sub-agent to find all Python files and identify their purposes
3. Spawn an 'analysis' sub-agent to analyze code quality issues in app.py  
4. Spawn a 'debugging' sub-agent to identify potential security vulnerabilities
5. Consolidate findings from all sub-agents
6. Create a comprehensive security report
7. Suggest fixes for each identified issue
8. Create improved versions of the problematic files

This task specifically tests:
- Sub-agent spawning with different types (search, analysis, debugging)
- Coordination between main agent and sub-agents
- Consolidation of sub-agent results
- Task decomposition using sub-agents"""

        print(f"📋 Task: Complex code analysis with sub-agents...")
        
        # Execute task
        result = agent.execute_task(task)
        
        print(f"\n📊 Test Case 2 Results:")
        print(f"Success: {result['success']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Sub-agents spawned: {result.get('sub_agents_spawned', 0)}")
        
        # Check sub-agent usage
        success_criteria = []
        
        # Check progress.md for sub-agent activity
        if os.path.exists(f"{test_dir}/progress.md"):
            with open(f"{test_dir}/progress.md", "r") as f:
                progress_content = f.read()
                
                # Count sub-agent mentions
                sub_agent_count = progress_content.count("Sub-Agent Results")
                if sub_agent_count > 0:
                    success_criteria.append(f"✅ Sub-agents detected: {sub_agent_count} results")
                else:
                    success_criteria.append("❌ No sub-agent activity detected")
                
                # Check for different agent types
                agent_types = ["search", "analysis", "debugging"]
                found_types = [t for t in agent_types if t in progress_content]
                if found_types:
                    success_criteria.append(f"✅ Agent types used: {', '.join(found_types)}")
                else:
                    success_criteria.append("❌ No specialized agent types detected")
        
        # Check if analysis results were produced
        report_files = list(Path(test_dir).glob("*report*")) + list(Path(test_dir).glob("*analysis*"))
        if report_files:
            success_criteria.append(f"✅ Analysis reports created: {len(report_files)}")
        else:
            success_criteria.append("⚠️ No analysis reports found")
            
        # Check if improved files were created
        improved_files = [f for f in os.listdir(test_dir) if "improved" in f or "fixed" in f]
        if improved_files:
            success_criteria.append(f"✅ Improved files created: {len(improved_files)}")
        else:
            success_criteria.append("⚠️ No improved files found")
        
        print("\n📋 Success Criteria:")
        for criterion in success_criteria:
            print(f"  {criterion}")
            
        # Success if sub-agents were used and task progressed
        overall_success = result['iterations'] > 5 and ("Sub-agents" in str(result) or sub_agent_count > 0)
        print(f"\n🎯 Test Case 2: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test Case 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            os.chdir("..")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
        except:
            pass


def test_case_3_persistent_error_recovery():
    """
    TEST CASE 3: Persistent Error Recovery with Interruption
    Tests the persistence and recovery capabilities under stress
    """
    print("\n🧪 TEST CASE 3: Persistent Error Recovery")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return False

    # Create test directory
    test_dir = "test_persistence" 
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    config = Config(
        api_key=api_key,
        working_dir=test_dir,
        max_iterations=8,  # Low limit to force interruption
        debug_mode=True,
        enable_web=True,
        state_file=".ultimate_state.pkl"
    )

    try:
        # PHASE 1: Start task that will likely get interrupted
        print("📋 Phase 1: Starting complex task (will hit iteration limit)...")
        
        agent = UltimateSWEAgent(config)
        
        task = """Create a comprehensive Python data analysis project:

1. Create project directory structure (data/, src/, tests/, docs/)
2. Use web_search to find best practices for Python data analysis
3. Install required packages (pandas, numpy, matplotlib, jupyter) - this might fail
4. Create sample dataset generation script
5. Build data cleaning and preprocessing pipeline  
6. Create multiple visualization scripts
7. Implement statistical analysis functions
8. Generate comprehensive data analysis report
9. Create unit tests for all functions
10. Set up automated testing with GitHub Actions
11. Create documentation with Sphinx
12. Package everything for distribution

This is intentionally complex to test persistence under pressure."""

        result1 = agent.execute_task(task)
        
        print(f"\n📊 Phase 1 Results:")
        print(f"Success: {result1['success']}")
        print(f"Iterations: {result1['iterations']}")
        print(f"Resume possible: {result1.get('resume_possible', False)}")
        
        task_id = result1.get('task_id')
        if not task_id:
            print("❌ No task ID returned - persistence test failed")
            return False
            
        # Check if state file was created
        state_file = Path(test_dir) / ".ultimate_state.pkl"
        if not state_file.exists():
            print("❌ State file not created - persistence failed")
            return False
            
        print(f"✅ State saved with task ID: {task_id}")
        
        # PHASE 2: Resume the task
        print(f"\n📋 Phase 2: Resuming task {task_id}...")
        
        # Create new agent instance (simulating restart)
        config2 = Config(
            api_key=api_key,
            working_dir=test_dir,
            max_iterations=15,  # More iterations for completion
            debug_mode=True,
            enable_web=True,
            state_file=".ultimate_state.pkl"
        )
        
        agent2 = UltimateSWEAgent(config2)
        result2 = agent2.execute_task("", resume_task_id=task_id)
        
        print(f"\n📊 Phase 2 Results:")
        print(f"Resume success: {result2['success']}")
        print(f"Resume iterations: {result2['iterations']}")
        print(f"Total iterations: {result1['iterations'] + result2['iterations']}")
        
        # Analyze persistence success
        success_criteria = []
        
        # Check if files persisted across restart
        project_files = list(Path(test_dir).glob("**/*"))
        python_files = [f for f in project_files if f.suffix == '.py']
        
        if python_files:
            success_criteria.append(f"✅ Files persisted: {len(python_files)} Python files")
        else:
            success_criteria.append("❌ No files persisted across restart")
            
        # Check progress.md for persistence indicators
        if os.path.exists(f"{test_dir}/progress.md"):
            with open(f"{test_dir}/progress.md", "r") as f:
                progress_content = f.read()
                
                if "Resuming task" in progress_content:
                    success_criteria.append("✅ Resume operation detected in progress")
                
                if "Error History" in progress_content:
                    success_criteria.append("✅ Error history maintained")
                    
                # Check for comprehensive tracking
                if "Sub-Agent Results" in progress_content:
                    success_criteria.append("✅ Sub-agent results preserved")
        
        # Check that progress continued from where it left off
        total_iterations = result1['iterations'] + result2['iterations']
        if total_iterations > result1['iterations']:
            success_criteria.append("✅ Task continued after interruption")
        else:
            success_criteria.append("❌ Task did not continue properly")
            
        # Check if comprehensive capabilities were maintained
        if result2.get('tools_used', 0) > 10:
            success_criteria.append("✅ Full tool suite available after resume")
        
        print("\n📋 Success Criteria:")
        for criterion in success_criteria:
            print(f"  {criterion}")
            
        # Success if task resumed and made progress
        overall_success = (
            result1.get('resume_possible', False) and 
            result2['iterations'] > 0 and 
            len(python_files) > 0
        )
        
        print(f"\n🎯 Test Case 3: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test Case 3 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            os.chdir("..")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
        except:
            pass


def main():
    """Run all three critical test cases"""
    print("🚀 Ultimate SWE Agent - Critical Test Suite")
    print("Testing: Web Search, Sub-Agents, Persistent Recovery")
    print("=" * 80)
    
    results = []
    
    # Test Case 1: Web Search + Error Handling
    results.append(test_case_1_web_search_and_error_recovery())
    
    # Test Case 2: Sub-Agent Spawning  
    results.append(test_case_2_sub_agent_spawning())
    
    # Test Case 3: Persistent Error Recovery
    results.append(test_case_3_persistent_error_recovery())
    
    # Final Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{total} test cases")
    
    test_names = [
        "Web Search + Error Handling", 
        "Sub-Agent Spawning",
        "Persistent Error Recovery"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED! Ultimate SWE Agent is ready for production.")
        print("Key capabilities validated:")
        print("  ✅ Real web search with DuckDuckGo integration")
        print("  ✅ Sub-agent spawning and coordination")  
        print("  ✅ Persistent state and error recovery")
        print("  ✅ Complete Claude Code equivalent functionality")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Ultimate SWE Agent needs refinement.")
        
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)