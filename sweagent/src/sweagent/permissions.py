"""
Permission management system for SWE Agent
"""

from pathlib import Path
from typing import Tuple


class PermissionManager:
    """Manages permissions for file operations and system commands"""
    
    SAFE_COMMANDS = [
        'ls', 'dir', 'pwd', 'whoami', 'date', 'git status', 'git log', 
        'npm list', 'pip list', 'python --version', 'node --version'
    ]
    
    ELEVATED_COMMANDS = [
        'mkdir', 'touch', 'cp', 'mv', 'chmod', 'python', 'node', 
        'npm install', 'pip install', 'pytest', 'flake8', 'black'
    ]
    
    ADMIN_COMMANDS = [
        'rm', 'rmdir', 'sudo', 'su', 'chown', 'systemctl', 'service'
    ]
    
    def __init__(self, permission_level: str = "safe"):
        self.permission_level = permission_level
    
    def check_command_permission(self, command: str) -> Tuple[bool, str]:
        """Check if command is allowed at current permission level"""
        command_lower = command.lower().strip()
        
        if any(command_lower.startswith(safe) for safe in self.SAFE_COMMANDS):
            return True, "safe"
        
        if self.permission_level in ["elevated", "admin"]:
            if any(command_lower.startswith(elevated) for elevated in self.ELEVATED_COMMANDS):
                return True, "elevated"
        
        if self.permission_level == "admin":
            if any(command_lower.startswith(admin) for admin in self.ADMIN_COMMANDS):
                return True, "admin"
        
        return False, f"Command '{command}' requires higher permissions"
    
    def check_file_permission(self, file_path: str, operation: str) -> Tuple[bool, str]:
        """Check if file operation is allowed"""
        path = Path(file_path)
        
        # Check if trying to access system files
        system_paths = ['/etc', '/usr', '/bin', '/sbin', '/var/log']
        if any(str(path).startswith(sys_path) for sys_path in system_paths):
            if self.permission_level != "admin":
                return False, f"Access to system path '{file_path}' requires admin permissions"
        
        # Check file operations
        if operation in ["read"]:
            return True, "read allowed"
        elif operation in ["write", "edit", "create"]:
            if self.permission_level in ["elevated", "admin"]:
                return True, "write allowed"
            else:
                return False, f"Write operation requires elevated permissions"
        elif operation in ["delete"]:
            if self.permission_level == "admin":
                return True, "delete allowed"
            else:
                return False, f"Delete operation requires admin permissions"
        
        return True, "operation allowed"