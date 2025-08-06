#!/usr/bin/env python3
"""
Simple usage example for SWE Agent
"""

import os
from sweagent import LangGraphTaskAgent, UserConfig

def main():
    # Set up your API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create a simple configuration
    config = UserConfig(
        interactive_mode=False,
        permission_level="safe",  # Safe operations only
        show_todo_updates=True,
        output_format="standard"
    )
    
    # Initialize the agent
    agent = LangGraphTaskAgent(api_key, config)
    
    # Execute a simple task
    result = agent.execute_task(
        "List all Python files in the current directory and analyze their structure"
    )
    
    # Display results
    print(f"\nTask completed with {result['success_rate']:.1%} success rate")
    print(f"Completed {result['subtasks_completed']}/{result['subtasks_total']} subtasks")
    
    if result.get('final_report'):
        print("\nFinal Report:")
        print("=" * 50)
        print(result['final_report'])

if __name__ == "__main__":
    main()