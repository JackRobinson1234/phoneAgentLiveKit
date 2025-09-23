from typing import Dict, Any, Optional
from .animal_control_state import AnimalControlState, StateResult

class StateMachine:
    """State machine engine for managing conversation flow"""
    
    def __init__(self):
        self.states: Dict[str, AnimalControlState] = {}
        self.current_state: Optional[AnimalControlState] = None
        self.context: Dict[str, Any] = {}
        self.conversation_history: list = []
        self.is_complete = False
    
    def add_state(self, state: AnimalControlState) -> None:
        """Add a state to the state machine"""
        self.states[state.name] = state
    
    def set_initial_state(self, state_name: str) -> None:
        """Set the initial state for the conversation"""
        if state_name not in self.states:
            raise ValueError(f"State '{state_name}' not found")
        self.current_state = self.states[state_name]
    
    def start_conversation(self) -> str:
        """Start the conversation and return the initial message"""
        if not self.current_state:
            raise RuntimeError("No initial state set")
        
        # Initialize context
        self.context['conversation_started'] = True
        self.context['turn_count'] = 0
        
        # Enter the initial state
        message = self.current_state.enter(self.context)
        self._log_interaction("SYSTEM", message)
        return message
    
    def process_user_input(self, user_input: str) -> str:
        """Process user input and return the response"""
        if not self.current_state:
            raise RuntimeError("No current state")
        
        if self.is_complete:
            return "This conversation has ended. Please start a new session."
        
        # Log user input
        self._log_interaction("USER", user_input)
        self.context['turn_count'] = self.context.get('turn_count', 0) + 1
        
        try:
            # Phase 1: Process input in current state to determine next action
            result, next_state_name, updated_context = self.current_state.process_input(
                user_input, self.context
            )
            
            # Update context with results from first phase
            self.context.update(updated_context)
            
            # Handle state transition if needed
            if result == StateResult.TRANSITION and next_state_name:
                # Perform the transition - the next state's enter method will generate the response
                response = self._handle_state_transition(next_state_name)
            else:
                # No transition, handle the result normally
                response = self._handle_state_result(result, next_state_name)
            
            # Log system response
            self._log_interaction("SYSTEM", response)
            return response
            
        except Exception as e:
            # Handle errors
            result, next_state_name, updated_context = self.current_state.handle_error(e, self.context)
            self.context.update(updated_context)
            
            response = self._handle_state_result(result, next_state_name)
            self._log_interaction("SYSTEM", response)
            return response
    
    def _handle_state_transition(self, next_state_name: str) -> str:
        """Handle state transition with a two-phase approach"""
        if next_state_name not in self.states:
            raise RuntimeError(f"Invalid transition to state: {next_state_name}")
        
        print(f"🔄 SYSTEM: STATE TRANSITION - Exiting '{self.current_state.name}' → Entering '{next_state_name}'")
        
        # Exit current state
        self.current_state.exit(self.context)
        self.current_state.reset_retry_count()
        
        # Transition to next state
        previous_state = self.current_state
        self.current_state = self.states[next_state_name]
        
        # Phase 2: Process in the new state with the updated context
        # This is the second LLM call that generates a response in the new state context
        response = self.current_state.process_state_entry(self.context, previous_state.name)
        
        print(f"🔄 SYSTEM: Now in state '{next_state_name}'")
        return response
    
    def _handle_state_result(self, result: StateResult, next_state_name: Optional[str]) -> str:
        """Handle the result of state processing"""
        if result == StateResult.CONTINUE:
            # Stay in current state, return message from LLM or fallback
            return self.context.get('message', 
                                  self.context.get('error_message', 
                                                 "I didn't understand that. Could you please try again?"))
        
        elif result == StateResult.TRANSITION:
            # This should now be handled by _handle_state_transition
            # This is kept for backward compatibility or direct calls
            return self._handle_state_transition(next_state_name) if next_state_name else \
                   "I'm not sure what to do next. Could you please try again?"
        
        elif result == StateResult.COMPLETE:
            # Before marking as complete, transition to FINAL_SUMMARY state if it exists
            if 'FINAL_SUMMARY' in self.states and self.current_state.name != 'FINAL_SUMMARY':
                print(f"🔄 SYSTEM: STATE TRANSITION - Exiting '{self.current_state.name}' → Entering 'FINAL_SUMMARY' for final summary")
                
                # Store the previous state in context
                self.context['previous_state'] = self.current_state.name
                
                # Transition to the final summary state
                previous_state = self.current_state
                self.current_state = self.states['FINAL_SUMMARY']
                
                # Process state entry for the final summary
                response = self.current_state.process_state_entry(self.context, previous_state.name)
                print(f"🔄 SYSTEM: Now in state 'FINAL_SUMMARY'")
                return response
            else:
                # If no FINAL_SUMMARY state or already in it, mark as complete
                self.is_complete = True
                return self.context.get('completion_message', 
                                      "Thank you! The conversation is complete.")
        
        elif result == StateResult.ERROR:
            # Handle error state
            if next_state_name and next_state_name in self.states:
                self.current_state.exit(self.context)
                self.current_state = self.states[next_state_name]
                return self.current_state.enter(self.context)
            else:
                self.is_complete = True
                return self.context.get('error_message', 
                                      "I'm sorry, but an error occurred and I cannot continue.")
        
        else:
            raise RuntimeError(f"Unknown state result: {result}")
    
    def _log_interaction(self, speaker: str, message: str) -> None:
        """Log an interaction to the conversation history"""
        from datetime import datetime
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'speaker': speaker,
            'message': message
        })
    
    def get_conversation_history(self) -> list:
        """Get the full conversation history"""
        return self.conversation_history.copy()
    
    def get_context(self) -> Dict[str, Any]:
        """Get the current context"""
        return self.context.copy()
    
    def reset(self) -> None:
        """Reset the state machine for a new conversation"""
        self.current_state = None
        self.context = {}
        self.conversation_history = []
        self.is_complete = False
        
        # Reset retry counts for all states
        for state in self.states.values():
            state.reset_retry_count()
    
    def get_current_state_name(self) -> Optional[str]:
        """Get the name of the current state"""
        return self.current_state.name if self.current_state else None
    
    def is_conversation_complete(self) -> bool:
        """Check if the conversation is complete"""
        return self.is_complete
