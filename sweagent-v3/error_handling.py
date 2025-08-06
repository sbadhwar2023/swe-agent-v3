"""
Enhanced error handling system for Ultimate SWE Agent
Provides comprehensive error categorization, recovery strategies, and analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import datetime
import traceback
import json
import logging
import time
from pathlib import Path

class ErrorCategory(Enum):
    """Comprehensive error categorization"""
    SYSTEM = "system"  # OS, filesystem, permissions
    NETWORK = "network"  # API calls, web requests
    TOOL = "tool"  # Tool-specific errors
    MODEL = "model"  # AI model related
    INPUT = "input"  # Invalid input/parameters
    STATE = "state"  # State management issues
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # Requires immediate attention
    HIGH = "high"  # Blocks progress
    MEDIUM = "medium"  # Affects functionality but has workaround
    LOW = "low"  # Minor issue
    INFO = "info"  # Informational

@dataclass
class ErrorContext:
    """Comprehensive error context"""
    timestamp: str
    error_type: str
    error_message: str
    stack_trace: str
    operation: str
    tool_name: Optional[str] = None
    input_data: Optional[Dict] = None
    state_snapshot: Optional[Dict] = None
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    recovery_attempts: int = 0
    related_errors: List[str] = field(default_factory=list)

@dataclass
class RecoveryStrategy:
    """Error recovery strategy"""
    strategy_type: str  # retry, fallback, delegate, skip, abort
    max_attempts: int
    backoff_factor: float
    timeout: int
    fallback_action: Optional[str] = None
    delegate_prompt: Optional[str] = None

class ErrorPatternAnalyzer:
    """Analyzes error patterns for predictive prevention"""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.pattern_cache: Dict[str, List[ErrorContext]] = {}
        
    def add_error(self, error: ErrorContext):
        """Add error to history and analyze patterns"""
        self.error_history.append(error)
        self._update_patterns(error)
        
    def _update_patterns(self, error: ErrorContext):
        """Update pattern analysis"""
        key = f"{error.category.value}:{error.tool_name}:{error.error_type}"
        if key not in self.pattern_cache:
            self.pattern_cache[key] = []
        self.pattern_cache[key].append(error)
        
        # Analyze for recurring patterns
        if len(self.pattern_cache[key]) >= 3:
            recent = self.pattern_cache[key][-3:]
            time_diffs = [
                (datetime.datetime.fromisoformat(recent[i+1].timestamp) - 
                 datetime.datetime.fromisoformat(recent[i].timestamp)).total_seconds()
                for i in range(len(recent)-1)
            ]
            if all(diff < 300 for diff in time_diffs):  # Pattern within 5 minutes
                logging.warning(f"Detected recurring error pattern: {key}")
                return True
        return False

class EnhancedErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self):
        self.analyzer = ErrorPatternAnalyzer()
        self.recovery_strategies: Dict[ErrorCategory, RecoveryStrategy] = self._init_strategies()
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup enhanced error logging"""
        logger = logging.getLogger("EnhancedErrorHandler")
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler("error_handling.log")
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
        
    def _init_strategies(self) -> Dict[ErrorCategory, RecoveryStrategy]:
        """Initialize recovery strategies for each error category"""
        return {
            ErrorCategory.SYSTEM: RecoveryStrategy(
                strategy_type="retry",
                max_attempts=3,
                backoff_factor=2.0,
                timeout=30
            ),
            ErrorCategory.NETWORK: RecoveryStrategy(
                strategy_type="retry",
                max_attempts=5,
                backoff_factor=1.5,
                timeout=60
            ),
            ErrorCategory.TOOL: RecoveryStrategy(
                strategy_type="fallback",
                max_attempts=2,
                backoff_factor=1.0,
                timeout=30,
                fallback_action="delegate"
            ),
            ErrorCategory.MODEL: RecoveryStrategy(
                strategy_type="fallback",
                max_attempts=2,
                backoff_factor=1.0,
                timeout=60,
                fallback_action="switch_model"
            ),
            ErrorCategory.INPUT: RecoveryStrategy(
                strategy_type="delegate",
                max_attempts=1,
                backoff_factor=1.0,
                timeout=30,
                delegate_prompt="Analyze and fix invalid input parameters"
            ),
            ErrorCategory.STATE: RecoveryStrategy(
                strategy_type="retry",
                max_attempts=2,
                backoff_factor=1.0,
                timeout=30
            ),
            ErrorCategory.UNKNOWN: RecoveryStrategy(
                strategy_type="delegate",
                max_attempts=1,
                backoff_factor=1.0,
                timeout=60,
                delegate_prompt="Analyze unknown error and recommend action"
            )
        }

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main error handling entry point"""
        error_context = self._create_error_context(error, context)
        self.logger.error(f"Handling error: {error_context.error_type} in {error_context.operation}")
        
        # Add to analyzer
        self.analyzer.add_error(error_context)
        
        # Get recovery strategy
        strategy = self.recovery_strategies[error_context.category]
        
        # Execute recovery
        return self._execute_recovery(error_context, strategy)
    
    def _create_error_context(self, error: Exception, context: Dict[str, Any]) -> ErrorContext:
        """Create comprehensive error context"""
        return ErrorContext(
            timestamp=datetime.datetime.now().isoformat(),
            error_type=error.__class__.__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            operation=context.get("operation", "unknown"),
            tool_name=context.get("tool_name"),
            input_data=context.get("input_data"),
            state_snapshot=context.get("state_snapshot"),
            category=self._categorize_error(error),
            severity=self._assess_severity(error),
            recovery_attempts=0
        )
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error type"""
        error_type = error.__class__.__name__.lower()
        
        if any(term in error_type for term in ["permission", "os", "file", "path"]):
            return ErrorCategory.SYSTEM
        elif any(term in error_type for term in ["connection", "timeout", "http", "network"]):
            return ErrorCategory.NETWORK
        elif "value" in error_type or "argument" in error_type:
            return ErrorCategory.INPUT
        elif "state" in error_type:
            return ErrorCategory.STATE
        elif "model" in error_type or "token" in error_type:
            return ErrorCategory.MODEL
        elif "tool" in error_type:
            return ErrorCategory.TOOL
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """Assess error severity"""
        error_type = error.__class__.__name__.lower()
        error_msg = str(error).lower()
        
        if any(term in error_msg for term in ["critical", "fatal", "crash"]):
            return ErrorSeverity.CRITICAL
        elif any(term in error_msg for term in ["permission", "access", "authentication"]):
            return ErrorSeverity.HIGH
        elif any(term in error_msg for term in ["timeout", "retry", "temporary"]):
            return ErrorSeverity.MEDIUM
        elif any(term in error_msg for term in ["warning", "deprecated"]):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _execute_recovery(
        self, 
        error_context: ErrorContext, 
        strategy: RecoveryStrategy
    ) -> Dict[str, Any]:
        """Execute recovery strategy"""
        self.logger.info(f"Executing {strategy.strategy_type} strategy for {error_context.category.value}")
        
        if error_context.recovery_attempts >= strategy.max_attempts:
            self.logger.error(f"Max recovery attempts ({strategy.max_attempts}) reached")
            return {
                "success": False,
                "error": "Max recovery attempts reached",
                "context": error_context,
                "action": "abort"
            }
        
        error_context.recovery_attempts += 1
        
        if strategy.strategy_type == "retry":
            return self._handle_retry(error_context, strategy)
        elif strategy.strategy_type == "fallback":
            return self._handle_fallback(error_context, strategy)
        elif strategy.strategy_type == "delegate":
            return self._handle_delegate(error_context, strategy)
        else:
            return {
                "success": False,
                "error": f"Unknown strategy type: {strategy.strategy_type}",
                "context": error_context,
                "action": "abort"
            }
    
    def _handle_retry(
        self, 
        error_context: ErrorContext, 
        strategy: RecoveryStrategy
    ) -> Dict[str, Any]:
        """Handle retry strategy"""
        delay = strategy.backoff_factor ** error_context.recovery_attempts
        self.logger.info(f"Retrying after {delay} seconds...")
        time.sleep(delay)
        
        return {
            "success": True,
            "action": "retry",
            "context": error_context,
            "delay": delay
        }
    
    def _handle_fallback(
        self, 
        error_context: ErrorContext, 
        strategy: RecoveryStrategy
    ) -> Dict[str, Any]:
        """Handle fallback strategy"""
        if strategy.fallback_action == "switch_model":
            return {
                "success": True,
                "action": "switch_model",
                "context": error_context,
                "new_model": "claude-3-opus-20240229"  # Fallback to more capable model
            }
        elif strategy.fallback_action == "delegate":
            return self._handle_delegate(error_context, strategy)
        
        return {
            "success": False,
            "error": f"Unknown fallback action: {strategy.fallback_action}",
            "context": error_context,
            "action": "abort"
        }
    
    def _handle_delegate(
        self, 
        error_context: ErrorContext, 
        strategy: RecoveryStrategy
    ) -> Dict[str, Any]:
        """Handle delegation to sub-agent"""
        if not strategy.delegate_prompt:
            return {
                "success": False,
                "error": "No delegation prompt provided",
                "context": error_context,
                "action": "abort"
            }
            
        return {
            "success": True,
            "action": "delegate",
            "context": error_context,
            "prompt": strategy.delegate_prompt,
            "agent_type": "debugging"
        }

class ModelSelector:
    """Intelligent model selection and fallback"""
    
    DEFAULT_MODELS = {
        "default": "claude-3-sonnet-20240229",
        "enhanced": "claude-3-opus-20240229",
        "fallback": "claude-3-haiku-20240307"
    }
    
    def __init__(self):
        self.current_model = self.DEFAULT_MODELS["default"]
        self.error_counts: Dict[str, int] = {}
        self.switch_threshold = 3  # Number of errors before switching models
        
    def get_model(self, context: Optional[Dict] = None) -> str:
        """Get appropriate model based on context"""
        if not context:
            return self.current_model
            
        # Use enhanced model for complex operations
        if self._is_complex_operation(context):
            self.current_model = self.DEFAULT_MODELS["enhanced"]
            return self.current_model
            
        return self.current_model
    
    def handle_error(self, error: Exception, context: Dict) -> str:
        """Handle model error and return new model if needed"""
        model = context.get("model", self.current_model)
        
        if model not in self.error_counts:
            self.error_counts[model] = 0
        self.error_counts[model] += 1
        
        if self.error_counts[model] >= self.switch_threshold:
            if model == self.DEFAULT_MODELS["default"]:
                self.current_model = self.DEFAULT_MODELS["enhanced"]
            elif model == self.DEFAULT_MODELS["enhanced"]:
                self.current_model = self.DEFAULT_MODELS["fallback"]
                
            self.error_counts[model] = 0
            return self.current_model
            
        return model
    
    def _is_complex_operation(self, context: Dict) -> bool:
        """Determine if operation is complex enough for enhanced model"""
        operation = context.get("operation", "").lower()
        tool_name = context.get("tool_name", "").lower()
        
        complex_indicators = [
            "debug",
            "analyze",
            "error",
            "recovery",
            "task_agent",
            "create_summary"
        ]
        
        return any(indicator in operation or indicator in tool_name 
                  for indicator in complex_indicators)