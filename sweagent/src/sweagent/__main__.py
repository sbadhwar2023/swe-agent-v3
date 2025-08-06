"""
Main CLI entry point for SWE Agent
"""

import os
import argparse
import logging
from pathlib import Path

from .agent import LangGraphTaskAgent
from .config import UserConfig, load_config_from_file, create_sample_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_cli_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SWE Agent - Software Engineering Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m sweagent "Create a web app"
  python -m sweagent --config config.yaml
  python -m sweagent --interactive --permission elevated "Deploy the application"
  python -m sweagent --create-config config.yaml
        """
    )
    
    parser.add_argument(
        'task', 
        nargs='?', 
        help='Task description to execute'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    
    parser.add_argument(
        '--create-config',
        type=str,
        metavar='PATH',
        help='Create a sample configuration file'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enable interactive mode'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Disable interactive mode'
    )
    
    parser.add_argument(
        '--permission',
        choices=['safe', 'elevated', 'admin'],
        help='Set permission level'
    )
    
    parser.add_argument(
        '--show-todos',
        action='store_true',
        help='Show todo list updates'
    )
    
    parser.add_argument(
        '--hide-todos',
        action='store_true',
        help='Hide todo list updates'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['minimal', 'standard', 'detailed'],
        help='Set output format'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        help='Maximum number of iterations'
    )
    
    parser.add_argument(
        '--working-dir',
        type=str,
        help='Working directory for operations'
    )
    
    return parser.parse_args()


def main():
    """Main CLI entry point"""
    args = parse_cli_arguments()
    
    # Handle config file creation
    if args.create_config:
        create_sample_config(args.create_config)
        return
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = UserConfig()
    
    # Override config with CLI arguments
    if args.interactive:
        config.interactive_mode = True
    elif args.non_interactive:
        config.interactive_mode = False
    
    if args.permission:
        config.permission_level = args.permission
    
    if args.show_todos:
        config.show_todo_updates = True
    elif args.hide_todos:
        config.show_todo_updates = False
    
    if args.output_format:
        config.output_format = args.output_format
    
    if args.max_iterations:
        config.max_iterations = args.max_iterations
    
    if args.working_dir:
        config.working_directory = args.working_dir
        os.chdir(args.working_dir)
    
    # Get task description
    if args.task:
        config.task_description = args.task
    elif not config.task_description:
        if config.interactive_mode:
            config.task_description = input("Enter task description: ").strip()
            if not config.task_description:
                print("❌ No task description provided.")
                return
        else:
            print("❌ No task description provided. Use --task or configure in config file.")
            return
    
    # Initialize API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Display configuration
    print("🚀 SWE Agent - Software Engineering Agent")
    print(f"📋 Task: {config.task_description}")
    print(f"🔐 Permission Level: {config.permission_level}")
    print(f"🎛️  Interactive Mode: {'Yes' if config.interactive_mode else 'No'}")
    print(f"📝 Todo Updates: {'Enabled' if config.show_todo_updates else 'Disabled'}")
    print(f"📁 Working Directory: {config.working_directory}")
    
    # Create and configure agent
    try:
        agent = LangGraphTaskAgent(api_key, config)
        
        # Execute task
        result = agent.execute_task(
            config.task_description,
            context={
                "working_directory": config.working_directory,
                "permission_level": config.permission_level,
                "interactive_mode": config.interactive_mode
            }
        )
        
        # Display results based on output format
        if config.output_format == "minimal":
            success = result.get('success_rate', 0) > 0.5
            print(f"\n{'✅' if success else '❌'} Task {'completed' if success else 'failed'}")
        elif config.output_format == "standard": 
            print(f"\n📊 Results:")
            print(f"Success Rate: {result.get('success_rate', 0):.1%}")
            print(f"Subtasks: {result.get('subtasks_completed', 0)}/{result.get('subtasks_total', 0)}")
        else:  # detailed
            print(f"\n📊 Detailed Results:")
            print(f"Success Rate: {result.get('success_rate', 0):.1%}")
            print(f"Subtasks: {result.get('subtasks_completed', 0)}/{result.get('subtasks_total', 0)}")
            if result.get('final_report'):
                print(f"\n📄 Final Report:\n{result['final_report']}")
        
        # Show todo summary
        if config.show_todo_updates:
            agent.todo_manager.display_full_list()
    
    except KeyboardInterrupt:
        print("\n👋 Execution interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main()