#!/usr/bin/env python3
"""
Advanced usage example for SWE Agent demonstrating complex task execution
"""

import os
from sweagent import LangGraphTaskAgent, UserConfig

def create_web_app():
    """Example: Create a complete web application"""
    
    config = UserConfig(
        interactive_mode=True,
        permission_level="elevated",
        show_todo_updates=True,
        max_iterations=20,
        output_format="detailed",
        working_directory="./web_app_project"
    )
    
    agent = LangGraphTaskAgent(os.getenv("ANTHROPIC_API_KEY"), config)
    
    task = """
    Create a complete Flask web application with the following features:
    1. User authentication (login/logout/register)
    2. SQLite database integration
    3. RESTful API endpoints
    4. HTML templates with Bootstrap styling
    5. Basic error handling and logging
    6. Requirements.txt file
    7. README with setup instructions
    """
    
    result = agent.execute_task(task, context={
        "framework": "Flask",
        "database": "SQLite", 
        "styling": "Bootstrap",
        "authentication": "Flask-Login"
    })
    
    return result

def analyze_codebase():
    """Example: Comprehensive codebase analysis"""
    
    config = UserConfig(
        interactive_mode=False,
        permission_level="safe",
        show_todo_updates=True,
        output_format="detailed"
    )
    
    agent = LangGraphTaskAgent(os.getenv("ANTHROPIC_API_KEY"), config)
    
    task = """
    Perform a comprehensive analysis of this codebase:
    1. Identify all Python files and their purposes
    2. Analyze code complexity and quality metrics
    3. Find potential security vulnerabilities
    4. Suggest architectural improvements
    5. Generate documentation for undocumented functions
    6. Create a dependency analysis report
    """
    
    result = agent.execute_task(task)
    return result

def automated_testing():
    """Example: Set up automated testing pipeline"""
    
    config = UserConfig(
        interactive_mode=True,
        permission_level="elevated",
        show_todo_updates=True,
        max_iterations=12
    )
    
    agent = LangGraphTaskAgent(os.getenv("ANTHROPIC_API_KEY"), config)
    
    task = """
    Set up a comprehensive testing pipeline:
    1. Create unit tests for all existing functions
    2. Set up pytest configuration
    3. Add code coverage reporting
    4. Create integration tests for API endpoints
    5. Set up GitHub Actions workflow for CI/CD
    6. Add pre-commit hooks for code quality
    """
    
    result = agent.execute_task(task, context={
        "testing_framework": "pytest",
        "coverage_tool": "pytest-cov",
        "ci_platform": "GitHub Actions"
    })
    
    return result

def main():
    """Run examples based on user choice"""
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY environment variable")
        return
    
    print("SWE Agent Advanced Usage Examples")
    print("=================================")
    print("1. Create Web Application")
    print("2. Analyze Codebase") 
    print("3. Setup Testing Pipeline")
    
    choice = input("\nSelect example (1-3): ").strip()
    
    if choice == "1":
        print("\n🚀 Creating web application...")
        result = create_web_app()
    elif choice == "2":
        print("\n🔍 Analyzing codebase...")
        result = analyze_codebase()
    elif choice == "3":
        print("\n🧪 Setting up testing pipeline...")
        result = automated_testing()
    else:
        print("Invalid choice")
        return
    
    # Display results
    print(f"\n📊 Execution Summary:")
    print(f"Success Rate: {result.get('success_rate', 0):.1%}")
    print(f"Subtasks: {result.get('subtasks_completed', 0)}/{result.get('subtasks_total', 0)}")
    
    if result.get('final_report'):
        print(f"\n📄 Final Report:")
        print("=" * 80)
        print(result['final_report'])

if __name__ == "__main__":
    main()