from typing import Dict, Any, Optional
from datetime import datetime

from models.database import MockDatabase
from state_machine.state_machine import StateMachine
from state_machine.llm_states import (
    LLMGreetingState, LLMCollectPatientInfoState, LLMCollectAppointmentTypeState,
    LLMCollectDoctorPreferenceState, LLMCollectDateTimeState
)
from state_machine.states import (
    ShowAvailabilityState, ConfirmAppointmentState, BookingCompleteState, ErrorHandlingState
)
from .conversation_handler import ConversationHandler
from .llm_nlp_processor import LLMNLPProcessor
from .llm_service import llm_service
from config.settings import AGENT_CONFIG

class LLMHealthAgent:
    """LLM-enhanced health agent orchestrator for appointment scheduling"""
    
    def __init__(self):
        self.database = MockDatabase()
        self.state_machine = StateMachine()
        self.conversation_handler = ConversationHandler()
        self.nlp_processor = LLMNLPProcessor()
        self.session_id = None
        self.is_initialized = False
        self.llm_enabled = True
        
        # Test LLM connection
        try:
            if not llm_service.test_connection():
                print("⚠️  Warning: LLM connection failed, falling back to basic mode")
                self.llm_enabled = False
        except Exception as e:
            print(f"⚠️  Warning: LLM initialization failed ({e}), using fallback mode")
            self.llm_enabled = False
        
        self._initialize_state_machine()
    
    def _initialize_state_machine(self):
        """Initialize the state machine with LLM-enhanced states"""
        if self.llm_enabled:
            # Use LLM-enhanced states
            states = [
                LLMGreetingState(self.database),
                LLMCollectPatientInfoState(self.database),
                LLMCollectAppointmentTypeState(self.database),
                LLMCollectDoctorPreferenceState(self.database),
                LLMCollectDateTimeState(self.database),
                ShowAvailabilityState(self.database),  # Keep original for now
                ConfirmAppointmentState(self.database),
                BookingCompleteState(self.database),
                ErrorHandlingState(self.database)
            ]
        else:
            # Fallback to original states
            from state_machine.states import (
                GreetingState, CollectPatientInfoState, CollectAppointmentTypeState,
                CollectDoctorPreferenceState, CollectDateTimeState
            )
            states = [
                GreetingState(self.database),
                CollectPatientInfoState(self.database),
                CollectAppointmentTypeState(self.database),
                CollectDoctorPreferenceState(self.database),
                CollectDateTimeState(self.database),
                ShowAvailabilityState(self.database),
                ConfirmAppointmentState(self.database),
                BookingCompleteState(self.database),
                ErrorHandlingState(self.database)
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
            raise RuntimeError("Health agent not properly initialized")
        
        # Start conversation handler session
        self.session_id = self.conversation_handler.start_session()
        
        # Start state machine
        initial_message = self.state_machine.start_conversation()
        
        # Add LLM status indicator
        if self.llm_enabled:
            initial_message += "\n\n🤖 *Enhanced with AI-powered understanding*"
        
        return initial_message
    
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
            # Get current state and context
            current_state = self.state_machine.get_current_state_name()
            current_context = self.state_machine.get_context()
            
            # Process input through conversation handler (now with LLM NLP)
            enhanced_context = self.conversation_handler.process_user_input(
                user_input, current_state, current_context
            )
            
            # Update state machine context
            self.state_machine.context.update(enhanced_context)
            
            # Process through state machine
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
            'conversation_summary': self.conversation_handler.get_conversation_summary(),
            'context_keys': list(self.state_machine.context.keys()),
            'llm_enabled': self.llm_enabled
        }
        
        # Add LLM-specific information
        if self.llm_enabled and 'last_llm_response' in self.state_machine.context:
            llm_info = self.state_machine.context['last_llm_response']
            status['last_llm_model'] = llm_info.get('model')
            status['llm_tool_calls'] = len(llm_info.get('tool_calls', []))
        
        return status
    
    def get_appointment_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of the current appointment being scheduled"""
        context = self.state_machine.get_context()
        
        if 'appointment_id' not in context:
            return None
        
        appointment = self.database.get_appointment(context['appointment_id'])
        if not appointment:
            return None
        
        doctor = self.database.get_doctor(appointment.doctor_id)
        patient = self.database.get_patient(appointment.patient_id)
        
        return {
            'appointment_id': appointment.id,
            'patient_name': patient.name if patient else 'Unknown',
            'doctor_name': f"Dr. {doctor.name}" if doctor else 'Unknown',
            'specialty': doctor.specialty if doctor else 'Unknown',
            'appointment_datetime': appointment.get_formatted_datetime(),
            'appointment_type': appointment.appointment_type.value.title(),
            'status': appointment.status.value.title(),
            'created_at': appointment.created_at.isoformat(),
            'llm_enhanced': self.llm_enabled
        }
    
    def get_available_doctors(self) -> list:
        """Get list of available doctors"""
        doctors = self.database.get_all_doctors()
        return [
            {
                'id': doctor.id,
                'name': f"Dr. {doctor.name}",
                'specialty': doctor.specialty,
                'available_days': doctor.available_days,
                'available_hours': doctor.available_hours
            }
            for doctor in doctors
        ]
    
    def get_available_specialties(self) -> list:
        """Get list of available medical specialties"""
        return self.database.get_available_specialties()
    
    def reset_conversation(self) -> str:
        """Reset the conversation and start fresh"""
        # Reset state machine
        self.state_machine.reset()
        
        # Reset conversation handler
        self.conversation_handler.reset_session()
        
        # Clear session
        self.session_id = None
        
        # Re-initialize state machine
        self.state_machine.set_initial_state("GREETING")
        
        # Start new conversation
        return self.start_conversation()
    
    def end_conversation(self) -> str:
        """End the current conversation gracefully"""
        if self.session_id:
            summary = self.conversation_handler.get_conversation_summary()
            
            # Reset everything
            self.state_machine.reset()
            self.conversation_handler.reset_session()
            self.session_id = None
            
            return "Thank you for using HealthBot! Your conversation has been ended. Have a great day!"
        
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
        stats = {
            'total_doctors': len(self.database.doctors),
            'total_patients': len(self.database.patients),
            'total_appointments': len(self.database.appointments),
            'available_specialties': len(self.database.get_available_specialties()),
            'active_doctors': len([d for d in self.database.doctors.values() if d.is_active]),
            'llm_enabled': self.llm_enabled
        }
        
        # Add LLM-specific stats
        if self.llm_enabled:
            try:
                stats['llm_connection_test'] = llm_service.test_connection()
                stats['available_models'] = llm_service.get_available_models()
            except:
                stats['llm_connection_test'] = False
        
        return stats
    
    def test_llm_integration(self) -> Dict[str, Any]:
        """Test LLM integration and return diagnostics"""
        results = {
            'llm_service_available': False,
            'nlp_processor_working': False,
            'connection_test': False,
            'sample_analysis': None,
            'error': None
        }
        
        try:
            # Test LLM service
            results['llm_service_available'] = True
            results['connection_test'] = llm_service.test_connection()
            
            # Test NLP processor
            sample_result = self.nlp_processor.process_input("I need to schedule an appointment with a cardiologist")
            results['nlp_processor_working'] = sample_result.get('method') == 'llm'
            results['sample_analysis'] = {
                'intent': sample_result.get('intent'),
                'confidence': sample_result.get('confidence'),
                'specialty': sample_result.get('specialty'),
                'method': sample_result.get('method')
            }
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
