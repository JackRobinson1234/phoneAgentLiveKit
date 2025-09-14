import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

from .llm_service import llm_service, tool_manager
from .nlp_processor import Intent, NLPProcessor
from config.settings import AVAILABLE_MODELS

class LLMNLPProcessor:
    """LLM-enhanced NLP processor that uses OpenRouter for intent detection and entity extraction"""
    
    def __init__(self):
        self.fallback_processor = NLPProcessor()  # Keep original as fallback
        self.model = AVAILABLE_MODELS.get('intent_detection')
        
    def process_input(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process user input using LLM for enhanced understanding
        
        Args:
            text: User input text
            context: Optional conversation context
            
        Returns:
            Dictionary with extracted information and confidence scores
        """
        if not text or not text.strip():
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'raw_text': text,
                'method': 'fallback'
            }
        
        try:
            # Use LLM for processing
            result = self._process_with_llm(text, context or {})
            result['method'] = 'llm'
            return result
            
        except Exception as e:
            # Fallback to original processor
            result = self.fallback_processor.process_input(text)
            result['method'] = 'fallback'
            result['llm_error'] = str(e)
            return result
    
    def _process_with_llm(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process input using LLM with tools"""
        
        # Build system prompt for NLP analysis
        system_prompt = """You are an expert NLP processor for a medical appointment scheduling system.

Your task is to analyze user input and extract relevant information using the provided tools.

Guidelines:
- Use analyze_appointment_request for intent detection and appointment preferences
- Use extract_patient_info for names, contact information
- Use parse_datetime_request for date/time expressions
- Provide confidence scores (0-1) for your extractions
- Be conservative with confidence - only high confidence (>0.8) for clear, unambiguous information
- Handle medical terminology and appointment-related language appropriately

Always use the appropriate tools to structure your analysis."""
        
        # Add context information
        context_info = ""
        if context:
            context_parts = []
            if context.get('current_state'):
                context_parts.append(f"Current state: {context['current_state']}")
            if context.get('patient_name'):
                context_parts.append(f"Patient: {context['patient_name']}")
            if context.get('turn_count'):
                context_parts.append(f"Turn: {context['turn_count']}")
            
            if context_parts:
                context_info = f"\nContext: {'; '.join(context_parts)}"
        
        messages = [
            {"role": "system", "content": system_prompt + context_info},
            {"role": "user", "content": f"Analyze this input: '{text}'"}
        ]
        
        # Get all tools for comprehensive analysis
        tools = [
            tool_manager.get_tool("analyze_appointment_request"),
            tool_manager.get_tool("extract_patient_info"),
            tool_manager.get_tool("parse_datetime_request")
        ]
        tools = [tool for tool in tools if tool is not None]
        
        # Make LLM call
        response = llm_service.chat_completion(
            messages=messages,
            tools=tools,
            model=self.model,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        # Process results
        result = {
            'raw_text': text,
            'intent': Intent.UNKNOWN,
            'confidence': 0.0,
            'appointment_type': None,
            'specialty': None,
            'doctor_name': None,
            'urgency': 'normal',
            'contact_info': {'email': None, 'phone': None},
            'name': None,
            'time_preferences': {},
            'llm_response': response.content
        }
        
        # Extract information from tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                self._process_tool_result(tool_call, result)
        
        # Set overall confidence as average of individual confidences
        confidences = []
        for key in ['intent_confidence', 'patient_confidence', 'datetime_confidence']:
            if key in result:
                confidences.append(result[key])
        
        if confidences:
            result['confidence'] = sum(confidences) / len(confidences)
        else:
            result['confidence'] = 0.1  # Low confidence if no tools were called
        
        return result
    
    def _process_tool_result(self, tool_call, result: Dict[str, Any]) -> None:
        """Process individual tool call results"""
        tool_name = tool_call.name
        args = tool_call.arguments
        
        if tool_name == "analyze_appointment_request":
            # Map intent string to enum
            intent_map = {
                'schedule': Intent.SCHEDULE_APPOINTMENT,
                'reschedule': Intent.RESCHEDULE_APPOINTMENT,
                'cancel': Intent.CANCEL_APPOINTMENT,
                'inquiry': Intent.GET_INFO,
                'other': Intent.UNKNOWN
            }
            
            if args.get('intent'):
                result['intent'] = intent_map.get(args['intent'], Intent.UNKNOWN)
            
            result['appointment_type'] = args.get('appointment_type')
            result['specialty'] = args.get('specialty')
            result['doctor_name'] = args.get('doctor_name')
            result['urgency'] = args.get('urgency', 'normal')
            result['intent_confidence'] = args.get('confidence', 0.0)
            
        elif tool_name == "extract_patient_info":
            result['name'] = args.get('name')
            if args.get('email'):
                result['contact_info']['email'] = args['email']
            if args.get('phone'):
                result['contact_info']['phone'] = args['phone']
            result['patient_confidence'] = args.get('confidence', 0.0)
            
        elif tool_name == "parse_datetime_request":
            time_prefs = {}
            if args.get('date'):
                time_prefs['parsed_date'] = args['date']
            if args.get('time'):
                time_prefs['parsed_time'] = args['time']
            if args.get('relative_reference'):
                time_prefs['relative_reference'] = args['relative_reference']
            if args.get('flexibility'):
                time_prefs['flexibility'] = args['flexibility']
            
            result['time_preferences'] = time_prefs
            result['datetime_confidence'] = args.get('confidence', 0.0)
    
    def extract_intent(self, text: str, context: Dict[str, Any] = None) -> Intent:
        """Extract user intent from text"""
        result = self.process_input(text, context)
        return result.get('intent', Intent.UNKNOWN)
    
    def extract_appointment_type(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Extract appointment type from text"""
        result = self.process_input(text, context)
        return result.get('appointment_type')
    
    def extract_specialty(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Extract medical specialty from text"""
        result = self.process_input(text, context)
        return result.get('specialty')
    
    def extract_doctor_name(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Extract doctor name from text"""
        result = self.process_input(text, context)
        return result.get('doctor_name')
    
    def extract_contact_info(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Optional[str]]:
        """Extract email and phone number from text"""
        result = self.process_input(text, context)
        return result.get('contact_info', {'email': None, 'phone': None})
    
    def extract_name(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Extract person name from text"""
        result = self.process_input(text, context)
        return result.get('name')
    
    def calculate_confidence(self, text: str, extracted_data: Dict, context: Dict[str, Any] = None) -> float:
        """Calculate confidence score for extracted information"""
        return extracted_data.get('confidence', 0.0)
    
    def test_llm_connection(self) -> bool:
        """Test LLM connection"""
        try:
            result = self.process_input("Hello, I need an appointment")
            return result.get('method') == 'llm'
        except Exception:
            return False
