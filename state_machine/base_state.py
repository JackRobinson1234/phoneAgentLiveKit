from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from enum import Enum

class StateResult(Enum):
    """Possible results from state execution"""
    CONTINUE = "continue"  # Stay in current state
    TRANSITION = "transition"  # Move to next state
    ERROR = "error"  # Error occurred
    COMPLETE = "complete"  # Conversation complete

class BaseState(ABC):
    """Abstract base class for all states in the appointment scheduling system"""
    
    def __init__(self, name: str):
        self.name = name
        self.retry_count = 0
        self.max_retries = 3
    
    @abstractmethod
    def enter(self, context: Dict[str, Any]) -> str:
        """
        Called when entering this state.
        Returns the message to display to the user.
        """
        pass
    
    @abstractmethod
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """
        Process user input and determine next action.
        
        Args:
            user_input: The user's input string
            context: Current conversation context
            
        Returns:
            Tuple of (StateResult, next_state_name, updated_context)
        """
        pass
    
    def exit(self, context: Dict[str, Any]) -> None:
        """
        Called when leaving this state.
        Can be used for cleanup or final processing.
        """
        pass
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """
        Handle errors that occur during state processing.
        
        Args:
            error: The exception that occurred
            context: Current conversation context
            
        Returns:
            Tuple of (StateResult, next_state_name, updated_context)
        """
        self.retry_count += 1
        
        if self.retry_count >= self.max_retries:
            context['error_message'] = f"Maximum retries exceeded in state {self.name}"
            return StateResult.ERROR, "ERROR_HANDLING", context
        
        context['error_message'] = f"An error occurred: {str(error)}. Please try again."
        return StateResult.CONTINUE, None, context
    
    def reset_retry_count(self):
        """Reset the retry counter"""
        self.retry_count = 0
    
    def validate_context(self, context: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that required keys exist in context.
        
        Args:
            context: Current conversation context
            required_keys: List of required context keys
            
        Returns:
            True if all required keys exist, False otherwise
        """
        return all(key in context for key in required_keys)
    
    def get_context_value(self, context: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Safely get a value from context with a default.
        
        Args:
            context: Current conversation context
            key: The key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The value from context or the default
        """
        return context.get(key, default)
