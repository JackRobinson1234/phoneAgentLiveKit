from typing import Dict, Any, Optional
import asyncio
from queue import Queue
from datetime import datetime
from .animal_control_state import AnimalControlState, StateResult
from .state_enum import StateEnum

class StateMachine:
    """State machine engine for managing conversation flow"""
    
    def __init__(self, call_logger=None):
        self.states: Dict[str, AnimalControlState] = {}
        self.current_state: Optional[AnimalControlState] = None
        self.context: Dict[str, Any] = {}
        self.conversation_history: list = []
        self.is_complete = False
        self._processing = False  # Track if currently processing
        self._input_queue = Queue()  # Queue for handling concurrent inputs
        self.call_logger = call_logger  # Optional call logger for analytics
        self._transition_start_time = None  # Track processing time
    
    def add_state(self, state: AnimalControlState) -> None:
        """Add a state to the state machine"""
        self.states[state.name] = state
    
    def set_initial_state(self, state_name: str) -> None:
        """Set the initial state for the conversation"""
        if state_name not in self.states:
            raise ValueError(f"State '{state_name}' not found")
        self.current_state = self.states[state_name]
    
    def start_conversation(self, session_id: str = None) -> str:
        """Start the conversation and return the initial message"""
        if not self.current_state:
            raise RuntimeError("No initial state set")
        
        # Initialize context (empty - no internal tracking fields)
        # Only business data will be added by states
        
        # Start call logging if logger is available
        if self.call_logger and session_id:
            self.call_logger.start_call(
                session_id=session_id,
                initial_state=self.current_state.name
            )
        
        # Enter the initial state
        message = self.current_state.enter(self.context)
        self._log_interaction("SYSTEM", message)
        return message
    
    def process_user_input(self, user_input: str) -> str:
        """Process user input and return the response (with concurrency protection)"""
        if not self.current_state:
            raise RuntimeError("No current state")
        
        if self.is_complete:
            return "This conversation has ended. Please start a new session."
        
        # Check if already processing - queue the input
        if self._processing:
            print(f"⚠️ SYSTEM: Already processing - queuing input: '{user_input}'")
            self._input_queue.put(user_input)
            # Return a placeholder - the queued input will be processed after current one
            return ""  # Empty response - the agent should handle this gracefully
        
        # Mark as processing
        self._processing = True
        
        try:
            # Process the current input
            response = self._process_input_internal(user_input)
            
            # Process any queued inputs
            while not self._input_queue.empty():
                queued_input = self._input_queue.get()
                print(f"🔄 SYSTEM: Processing queued input: '{queued_input}'")
                response = self._process_input_internal(queued_input)
            
            return response
        finally:
            # Always release the lock
            self._processing = False
    
    def _process_input_internal(self, user_input: str) -> str:
        """Internal method that does the actual processing"""
        # Track processing time
        self._transition_start_time = datetime.now()
        
        # Log user input
        self._log_interaction("USER", user_input)
        
        # Store current state for logging
        from_state = self.current_state.name
        
        try:
            # Phase 1: Process input in current state to determine next action
            result, next_state_name, updated_context = self.current_state.process_input(
                user_input, self.context
            )
            
            # Calculate context updates BEFORE updating self.context
            # This captures what actually changed
            internal_fields = {'message', 'last_llm_response', 'error_message', 'completion_message'}
            context_updates = {k: v for k, v in updated_context.items() 
                             if k not in internal_fields and (k not in self.context or self.context.get(k) != v)}
            
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
            
            # Log to call logger if available
            if self.call_logger:
                processing_time = int((datetime.now() - self._transition_start_time).total_seconds() * 1000)
                
                # Extract LLM stats from context
                llm_response = updated_context.get('last_llm_response', {})
                
                # Determine transition type
                if result == StateResult.TRANSITION:
                    transition_type = 'optimized' if updated_context.get('message') else 'fallback'
                else:
                    transition_type = 'continue'
                
                self.call_logger.log_transition(
                    from_state=from_state,
                    to_state=self.current_state.name,
                    user_input=user_input,
                    agent_response=response,
                    context=self.context,
                    context_updates=context_updates,
                    transition_type=transition_type,
                    llm_model=llm_response.get('model'),
                    llm_tokens=llm_response.get('usage', {}).get('total_tokens') if isinstance(llm_response.get('usage'), dict) else None,
                    processing_time_ms=processing_time
                )
            
            return response
            
        except Exception as e:
            # Handle errors
            result, next_state_name, updated_context = self.current_state.handle_error(e, self.context)
            self.context.update(updated_context)
            
            response = self._handle_state_result(result, next_state_name)
            self._log_interaction("SYSTEM", response)
            return response
    
    def _handle_state_transition(self, next_state_name: str) -> str:
        """Handle state transition with optimized single-LLM-call approach"""
        # Validate the state transition using the StateEnum
        if not StateEnum.is_valid_state(next_state_name):
            # If the requested state doesn't exist, log a warning and use CASE_CONFIRMATION as fallback
            print(f"⚠️ SYSTEM: WARNING - Attempted transition to non-existent state '{next_state_name}'")
            print(f"⚠️ SYSTEM: Using CASE_CONFIRMATION as fallback state")
            next_state_name = StateEnum.CASE_CONFIRMATION.value
        
        # Validate that this is a valid transition from the current state
        current_state_name = self.current_state.name
        valid_next_states = StateEnum.get_next_state_options(current_state_name)
        
        if next_state_name not in valid_next_states:
            print(f"⚠️ SYSTEM: WARNING - Invalid transition from '{current_state_name}' to '{next_state_name}'")
            print(f"⚠️ SYSTEM: Valid transitions are: {valid_next_states}")
            # Use the first valid transition as fallback
            if valid_next_states:
                next_state_name = valid_next_states[0]
                print(f"⚠️ SYSTEM: Using '{next_state_name}' as fallback state")
            else:
                # If no valid transitions, use CASE_CONFIRMATION as ultimate fallback
                next_state_name = StateEnum.CASE_CONFIRMATION.value
                print(f"⚠️ SYSTEM: Using '{next_state_name}' as ultimate fallback state")
        
        # Now check if the state exists in our state machine
        if next_state_name not in self.states:
            print(f"⚠️ INVALID TRANSITION - State '{next_state_name}' does not exist")
            raise RuntimeError(f"Invalid transition to state: {next_state_name}")
        
        # Check if there's a transition message from the LLM
        # With the optimized approach, the LLM should provide this
        transition_message = self.context.get('message')
        
        print(f"🔄 SYSTEM: STATE TRANSITION - Exiting '{self.current_state.name}' → Entering '{next_state_name}'")
        
        # Exit current state
        self.current_state.exit(self.context)
        self.current_state.reset_retry_count()
        
        # Transition to next state
        previous_state = self.current_state
        self.current_state = self.states[next_state_name]
        
        # OPTIMIZATION: Use the transition message if provided (single LLM call approach)
        # Only fall back to process_state_entry if no message was provided
        if transition_message and transition_message.strip():
            print(f"🔄 SYSTEM: Using transition message from previous state (OPTIMIZED - no second LLM call)")
            response = transition_message
        else:
            print(f"🔄 SYSTEM: No transition message provided, calling process_state_entry (FALLBACK - second LLM call)")
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
                
                # End call logging
                if self.call_logger:
                    self.call_logger.end_call(
                        final_state=self.current_state.name,
                        completion_status='completed'
                    )
                
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
