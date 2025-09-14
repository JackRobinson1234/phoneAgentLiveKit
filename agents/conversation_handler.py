from typing import Dict, Any, Optional
from datetime import datetime

from .nlp_processor import NLPProcessor, Intent
from .llm_nlp_processor import LLMNLPProcessor
from utils.validators import InputValidator

class ConversationHandler:
    """Handles conversation context and user input processing"""
    
    def __init__(self):
        # Try to use LLM-enhanced processor, fallback to basic if unavailable
        try:
            self.nlp_processor = LLMNLPProcessor()
            self.llm_enabled = True
        except Exception:
            self.nlp_processor = NLPProcessor()
            self.llm_enabled = False
        
        self.validator = InputValidator()
        self.session_data = {}
        self.conversation_started = False
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new conversation session"""
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.session_data = {
            'session_id': session_id,
            'started_at': datetime.now(),
            'turn_count': 0,
            'context': {},
            'user_preferences': {},
            'conversation_history': []
        }
        self.conversation_started = True
        return session_id
    
    def process_user_input(self, user_input: str, current_state: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user input and enrich context with extracted information
        
        Args:
            user_input: Raw user input text
            current_state: Current state machine state
            context: Current conversation context
            
        Returns:
            Enhanced context with extracted information
        """
        if not self.conversation_started:
            raise RuntimeError("Conversation session not started")
        
        # Sanitize input
        clean_input = self.validator.sanitize_input(user_input)
        
        # Process with NLP (LLM-enhanced if available)
        nlp_result = self.nlp_processor.process_input(clean_input, context)
        
        # Update session data
        self.session_data['turn_count'] += 1
        self.session_data['conversation_history'].append({
            'turn': self.session_data['turn_count'],
            'user_input': clean_input,
            'state': current_state,
            'timestamp': datetime.now(),
            'nlp_result': nlp_result
        })
        
        # Enrich context based on current state and NLP results
        enhanced_context = self._enrich_context(context, nlp_result, current_state)
        
        return enhanced_context
    
    def _enrich_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any], current_state: str) -> Dict[str, Any]:
        """Enrich context with NLP results based on current state"""
        enhanced_context = context.copy()
        
        # Always add NLP confidence and intent
        enhanced_context['nlp_confidence'] = nlp_result['confidence']
        enhanced_context['detected_intent'] = nlp_result['intent']
        
        # State-specific context enrichment
        if current_state == "GREETING":
            self._enrich_greeting_context(enhanced_context, nlp_result)
        
        elif current_state == "COLLECT_PATIENT_INFO":
            self._enrich_patient_info_context(enhanced_context, nlp_result)
        
        elif current_state == "COLLECT_APPOINTMENT_TYPE":
            self._enrich_appointment_type_context(enhanced_context, nlp_result)
        
        elif current_state == "COLLECT_DOCTOR_PREFERENCE":
            self._enrich_doctor_preference_context(enhanced_context, nlp_result)
        
        elif current_state == "COLLECT_DATE_TIME":
            self._enrich_datetime_context(enhanced_context, nlp_result)
        
        return enhanced_context
    
    def _enrich_greeting_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any]) -> None:
        """Enrich context for greeting state"""
        if nlp_result['intent'] == Intent.SCHEDULE_APPOINTMENT:
            context['user_ready_to_schedule'] = True
        
        if nlp_result['appointment_type']:
            context['suggested_appointment_type'] = nlp_result['appointment_type']
        
        if nlp_result['specialty']:
            context['suggested_specialty'] = nlp_result['specialty']
        
        if nlp_result['urgency'] != 'normal':
            context['urgency_level'] = nlp_result['urgency']
    
    def _enrich_patient_info_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any]) -> None:
        """Enrich context for patient info collection"""
        # Extract name if not already collected
        if 'patient_name' not in context and nlp_result['name']:
            if self.validator.validate_name(nlp_result['name']):
                context['suggested_name'] = nlp_result['name']
        
        # Extract contact info
        contact_info = nlp_result['contact_info']
        if contact_info['email'] and self.validator.validate_email(contact_info['email']):
            context['suggested_email'] = contact_info['email']
        
        if contact_info['phone'] and self.validator.validate_phone(contact_info['phone']):
            context['suggested_phone'] = self.validator.normalize_phone(contact_info['phone'])
    
    def _enrich_appointment_type_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any]) -> None:
        """Enrich context for appointment type collection"""
        if nlp_result['appointment_type']:
            context['suggested_appointment_type'] = nlp_result['appointment_type']
        
        # Store user preferences for future use
        if nlp_result['urgency'] != 'normal':
            context['urgency_preference'] = nlp_result['urgency']
    
    def _enrich_doctor_preference_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any]) -> None:
        """Enrich context for doctor preference collection"""
        if nlp_result['specialty']:
            context['suggested_specialty'] = nlp_result['specialty']
        
        if nlp_result['doctor_name']:
            context['suggested_doctor_name'] = nlp_result['doctor_name']
        
        # Check for "any" or "no preference" indicators
        raw_text = nlp_result['raw_text'].lower()
        if any(phrase in raw_text for phrase in ['any', 'no preference', 'don\'t care', 'whatever']):
            context['no_doctor_preference'] = True
    
    def _enrich_datetime_context(self, context: Dict[str, Any], nlp_result: Dict[str, Any]) -> None:
        """Enrich context for date/time collection"""
        time_prefs = nlp_result.get('time_preferences', {})
        
        if time_prefs.get('time_of_day'):
            context['preferred_time_of_day'] = time_prefs['time_of_day']
        
        if time_prefs.get('day_preference'):
            context['preferred_day'] = time_prefs['day_preference']
        
        if time_prefs.get('flexibility'):
            context['scheduling_flexibility'] = time_prefs['flexibility']
        
        # Store urgency for scheduling priority
        if nlp_result['urgency'] != 'normal':
            context['scheduling_urgency'] = nlp_result['urgency']
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation"""
        if not self.conversation_started:
            return {}
        
        return {
            'session_id': self.session_data['session_id'],
            'duration': datetime.now() - self.session_data['started_at'],
            'turn_count': self.session_data['turn_count'],
            'context_keys': list(self.session_data.get('context', {}).keys()),
            'avg_confidence': self._calculate_average_confidence(),
            'detected_intents': self._get_detected_intents()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average NLP confidence across the conversation"""
        confidences = [
            turn['nlp_result']['confidence'] 
            for turn in self.session_data['conversation_history']
            if 'nlp_result' in turn
        ]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _get_detected_intents(self) -> list:
        """Get list of unique intents detected in the conversation"""
        intents = [
            turn['nlp_result']['intent'].value 
            for turn in self.session_data['conversation_history']
            if 'nlp_result' in turn and turn['nlp_result']['intent'] != Intent.UNKNOWN
        ]
        return list(set(intents))
    
    def reset_session(self) -> None:
        """Reset the conversation session"""
        self.session_data = {}
        self.conversation_started = False
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Extract user preferences from conversation history"""
        preferences = {}
        
        for turn in self.session_data.get('conversation_history', []):
            nlp_result = turn.get('nlp_result', {})
            
            # Collect preferences
            if nlp_result.get('urgency') != 'normal':
                preferences['urgency_preference'] = nlp_result['urgency']
            
            if nlp_result.get('specialty'):
                preferences['preferred_specialty'] = nlp_result['specialty']
            
            time_prefs = nlp_result.get('time_preferences', {})
            if time_prefs.get('time_of_day'):
                preferences['preferred_time_of_day'] = time_prefs['time_of_day']
            
            if time_prefs.get('flexibility'):
                preferences['scheduling_flexibility'] = time_prefs['flexibility']
        
        return preferences
