from typing import Dict, Any, Optional
from datetime import datetime
import os

from src.models.animal_database import MockAnimalDatabase
from src.state_machine.state_machine import StateMachine
from src.state_machine.animal_control_state import AnimalControlState
from src.state_machine.animal_control_states import (
    LLMGreetingAndDetermineServiceState, LLMEmergencyCaseState,
    LLMReportFoundState, LLMReportLostState, LLMPetSurrenderState,
    LLMScheduleSurrenderState, LLMGeneralInfoState, LLMCaseConfirmationState,
    LLMCaseCompleteState, LLMErrorHandlingState, LLMFinalSummaryState
)
from .llm_service import get_llm_service
from src.logging import CallLogger

class LLMAnimalControlAgent:
    """LLM-enhanced animal control agent orchestrator"""
    
    def __init__(self):
        self.database = MockAnimalDatabase()
        
        # Initialize call logger if Supabase credentials are available
        self.call_logger = None
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            if supabase_url and supabase_key:
                self.call_logger = CallLogger(supabase_url, supabase_key)
                print("✅ Call logger initialized successfully")
            else:
                print("⚠️  Call logger disabled - Supabase credentials not found")
        except Exception as e:
            print(f"⚠️  Warning: Call logger initialization failed: {e}")
        
        # Initialize state machine with logger
        self.state_machine = StateMachine(call_logger=self.call_logger)
        self.session_id = None
        self.is_initialized = False
        self.llm_enabled = True
        
        # Test LLM connection
        try:
            if not get_llm_service().test_connection():
                print("⚠️  Warning: LLM connection failed")
                raise RuntimeError("LLM connection failed")
        except Exception as e:
            print(f"⚠️  Warning: LLM initialization failed: {e}")
            raise
        
        self._initialize_state_machine()
    
    def _initialize_state_machine(self):
        """Initialize the state machine with LLM-enhanced states"""
        # Use LLM-enhanced states
        states = [
            LLMGreetingAndDetermineServiceState(),
            LLMEmergencyCaseState(),
            LLMReportFoundState(),
            LLMReportLostState(),
            LLMPetSurrenderState(),
            LLMScheduleSurrenderState(),
            LLMGeneralInfoState(),
            LLMCaseConfirmationState(),
            LLMCaseCompleteState(),
            LLMErrorHandlingState(),
            LLMFinalSummaryState()
        ]
        
        # Add states to state machine
        for state in states:
            self.state_machine.add_state(state)
        
        # Set initial state
        self.state_machine.set_initial_state("GREETING")
        self.is_initialized = True
    
    def start_conversation(self) -> str:
        """Start a new conversation session"""
        if not self.is_initialized:
            raise RuntimeError("Animal control agent not properly initialized")
        
        # Generate session ID
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"🎬 Starting conversation with session ID: {self.session_id}")
        
        # Reset context for new conversation
        self.state_machine.context.clear()
        
        # Create a concise greeting message
        greeting = "Hello! I'm here to help with animal control services. How can I assist you today?"
        
        # Start state machine with session ID for logging
        self.state_machine.start_conversation(session_id=self.session_id)
        
        # Return the standardized greeting
        return greeting
    
    def process_message(self, user_input: str) -> str:
        """
        Process a user message and return the agent's response
        
        Args:
            user_input: The user's input message
            
        Returns:
            The agent's response message
        """
        if not self.session_id:
            raise RuntimeError("Conversation not started. Call start_conversation() first.")
        
        try:           
            
            # Process directly through state machine
            response = self.state_machine.process_user_input(user_input)
            
            return response
            
        except Exception as e:
            # Handle unexpected errors gracefully
            error_message = f"I apologize, but I encountered an unexpected error: {str(e)}"
            
            # Try to recover by transitioning to error handling state
            try:
                self.state_machine.context['error_message'] = error_message
                self.state_machine.current_state = self.state_machine.states['ERROR_HANDLING']
                return self.state_machine.current_state.enter(self.state_machine.context)
            except:
                return "I'm sorry, but I'm experiencing technical difficulties. Please try again later."
    
    def get_conversation_status(self) -> Dict[str, Any]:
        """Get the current status of the conversation"""
        if not self.session_id:
            return {'status': 'not_started'}
        
        status = {
            'status': 'active' if not self.state_machine.is_conversation_complete() else 'completed',
            'session_id': self.session_id,
            'current_state': self.state_machine.get_current_state_name(),
            'turn_count': self.state_machine.context.get('turn_count', 0),
            'context_keys': list(self.state_machine.context.keys())
        }
        
        # Add LLM-specific information
        if 'last_llm_response' in self.state_machine.context:
            llm_info = self.state_machine.context['last_llm_response']
            status['last_llm_model'] = llm_info.get('model')
            status['llm_tool_calls'] = len(llm_info.get('tool_calls', []))
        
        return status
    
    def get_case_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of the current case being processed"""
        context = self.state_machine.get_context()
        
        if 'case_id' not in context:
            return None
        
        case_details = context.get('case_details', {})
        
        return {
            'case_id': context.get('case_id'),
            'case_type': case_details.get('type', 'unknown'),
            'animal_type': case_details.get('animal_type', 'Unknown'),
            'location': case_details.get('location', case_details.get('location_found', case_details.get('last_seen_location', 'Unknown'))),
            'status': case_details.get('status', 'pending'),
            'created_at': case_details.get('timestamp', datetime.now().isoformat()),
            'llm_enhanced': self.llm_enabled
        }
    
    def get_available_services(self) -> list:
        """Get list of available animal control services"""
        return [
            {
                'id': 'emergency',
                'name': 'Injured, Abused, or Emergency Cases',
                'description': 'Report animals in immediate danger or distress'
            },
            {
                'id': 'found',
                'name': 'Report Found Animal',
                'description': 'Report a stray or found animal'
            },
            {
                'id': 'lost',
                'name': 'Report Lost Animal',
                'description': 'Report your lost pet'
            },
            {
                'id': 'surrender',
                'name': 'Schedule Pet Surrender',
                'description': 'Arrange to surrender a pet to animal control'
            }
        ]
    
    def reset_conversation(self) -> str:
        """Reset the conversation and start fresh"""
        # Reset state machine
        self.state_machine.reset()
        
        # Clear session
        self.session_id = None
        
        # Re-initialize state machine
        self._initialize_state_machine()
        
        # Start new conversation
        return self.start_conversation()
    
    def end_conversation(self) -> str:
        """End the current conversation gracefully"""
        if self.session_id:
            # Reset everything
            self.state_machine.reset()
            self.session_id = None
            
            return "Thank you for using AnimalControlBot! Your conversation has been ended. Have a great day!"
        
        return "No active conversation to end."
    
    def get_conversation_history(self) -> list:
        """Get the full conversation history"""
        return self.state_machine.get_conversation_history()
    
    def is_conversation_active(self) -> bool:
        """Check if there's an active conversation"""
        return (self.session_id is not None and 
                not self.state_machine.is_conversation_complete())
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the mock database"""
        stats = self.database.get_statistics()
        
        # Add LLM-specific stats
        try:
            stats['llm_connection_test'] = get_llm_service().test_connection()
            stats['available_models'] = get_llm_service().get_available_models()
        except:
            stats['llm_connection_test'] = False
        
        return stats
    
    def test_llm_integration(self) -> Dict[str, Any]:
        """Test LLM integration and return results"""
        results = {
            'llm_service_available': False,
            'connection_test': False,
            'sample_analysis': None,
            'error': None
        }
        
        try:
            # Test LLM service
            llm_svc = get_llm_service()
            results['llm_service_available'] = llm_svc is not None
            
            # Test connection
            results['connection_test'] = llm_svc.test_connection()
            
            # Test LLM with a sample request
            sample_text = "I found a stray dog"
            analysis = llm_svc.analyze_request(sample_text)
            results['sample_analysis'] = analysis
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
