from typing import Dict, Any, Optional
from datetime import datetime

from models.database import MockDatabase
from state_machine.state_machine import StateMachine
from state_machine.llm_states import (
    LLMGreetingState, LLMCollectPatientInfoState, LLMCollectAppointmentTypeState,
    LLMCollectDoctorPreferenceState, LLMCollectDateTimeState, LLMShowAvailabilityState, 
    LLMConfirmAppointmentState, LLMBookingCompleteState, LLMErrorHandlingState
)
from .llm_service import llm_service
from config.settings import AGENT_CONFIG

class LLMHealthAgent:
    """LLM-enhanced health agent orchestrator for appointment scheduling"""
    
    def __init__(self):
        self.database = MockDatabase()
        self.state_machine = StateMachine()
        self.session_id = None
        self.is_initialized = False
        
        # Test LLM connection
        try:
            if not llm_service.test_connection():
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
            LLMGreetingState(self.database),
            LLMCollectPatientInfoState(self.database),
            LLMCollectAppointmentTypeState(self.database),
            LLMCollectDoctorPreferenceState(self.database),
            LLMCollectDateTimeState(self.database),
            LLMShowAvailabilityState(self.database),
            LLMConfirmAppointmentState(self.database),
            LLMBookingCompleteState(self.database),
            LLMErrorHandlingState(self.database)
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
        
        # Generate session ID
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start state machine
        initial_message = self.state_machine.start_conversation()
        
        # Add LLM status indicator
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
            'active_doctors': len([d for d in self.database.doctors.values() if d.is_active])
        }
        
        # Add LLM-specific stats
        try:
            stats['llm_connection_test'] = llm_service.test_connection()
            stats['available_models'] = llm_service.get_available_models()
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
            results['llm_service_available'] = llm_service is not None
            
            # Test connection
            results['connection_test'] = llm_service.test_connection()
            
            # Test LLM with a sample request
            sample_text = "I need to see a doctor tomorrow"
            analysis = llm_service.analyze_appointment_request(sample_text)
            results['sample_analysis'] = analysis
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
