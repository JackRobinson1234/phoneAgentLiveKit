from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
import json

from .base_state import BaseState, StateResult
from agents.llm_service import llm_service, tool_manager
from config.settings import AVAILABLE_MODELS

class LLMEnhancedState(BaseState):
    """Enhanced base state that uses LLM for processing and response generation"""
    
    def __init__(self, name: str, system_prompt: str = None):
        super().__init__(name)
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.conversation_history = []
        self.model = AVAILABLE_MODELS.get('conversation')
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for this state"""
        return f"""You are HealthBot, an AI assistant helping users schedule doctor appointments. 
        
Current State: {self.name}
Your role: Process user input and guide them through the appointment scheduling process.

Guidelines:
- Be helpful, professional, and empathetic
- Ask for information step by step
- Validate user inputs appropriately
- Use the provided tools to extract information and generate responses
- Keep responses concise but informative
- Handle errors gracefully and offer alternatives

Always use the generate_response tool to provide your final response and next action."""
    
    def _build_messages(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build message history for LLM"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation context
        if context.get('conversation_history'):
            for entry in context['conversation_history'][-5:]:  # Last 5 exchanges
                if entry.get('speaker') == 'USER':
                    messages.append({"role": "user", "content": entry['message']})
                elif entry.get('speaker') == 'SYSTEM':
                    messages.append({"role": "assistant", "content": entry['message']})
        
        # Add current context information
        context_info = self._format_context_info(context)
        if context_info:
            messages.append({"role": "system", "content": f"Current context: {context_info}"})
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _format_context_info(self, context: Dict[str, Any]) -> str:
        """Format relevant context information for the LLM"""
        info_parts = []
        
        # Patient information
        if context.get('patient_name'):
            info_parts.append(f"Patient: {context['patient_name']}")
        if context.get('patient_contact'):
            info_parts.append(f"Contact: {context['patient_contact']}")
        
        # Appointment details
        if context.get('appointment_type'):
            info_parts.append(f"Appointment type: {context['appointment_type']}")
        if context.get('preferred_specialty'):
            info_parts.append(f"Specialty: {context['preferred_specialty']}")
        if context.get('preferred_datetime'):
            info_parts.append(f"Preferred time: {context['preferred_datetime']}")
        
        # Current progress
        if context.get('turn_count'):
            info_parts.append(f"Turn: {context['turn_count']}")
        
        return "; ".join(info_parts)
    
    def process_input_with_llm(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """Process input using LLM with appropriate tools"""
        try:
            # Build message history
            messages = self._build_messages(user_input, context)
            
            # Get tools for current state
            tools = tool_manager.get_tools_for_state(self.name)
            
            # Make LLM call
            print(f"🔧 SYSTEM: Making LLM call for state '{self.name}' with {len(tools)} tools available")
            response = llm_service.chat_completion(
                messages=messages,
                tools=tools,
                model=self.model
            )
            
            # Process tool calls
            updated_context = context.copy()
            final_response = None  # Don't use LLM content directly
            next_action = StateResult.CONTINUE
            next_state = None
            
            if response.tool_calls:
                print(f"🔧 SYSTEM: LLM made {len(response.tool_calls)} tool call(s)")
                for tool_call in response.tool_calls:
                    print(f"🔧 SYSTEM: Tool called - '{tool_call.name}' with args: {tool_call.arguments}")
                    result = self._handle_tool_call(tool_call, context, user_input)
                    if result:
                        updated_context.update(result.get('context_updates', {}))
                        if result.get('response'):
                            final_response = result['response']  # Use tool-generated response
                        if result.get('next_action'):
                            next_action = StateResult[result['next_action'].upper()]
                            print(f"🔧 SYSTEM: Tool set next_action to '{result['next_action']}'")
                        if result.get('next_state'):
                            next_state = result['next_state']
                            print(f"🔧 SYSTEM: Tool requested state transition to '{next_state}'")
            else:
                print(f"🔧 SYSTEM: LLM made no tool calls - will use fallback acknowledgment")
            
            # Store LLM interaction and response
            updated_context['last_llm_response'] = {
                'content': response.content,
                'tool_calls': [{'name': tc.name, 'args': tc.arguments} for tc in response.tool_calls] if response.tool_calls else [],
                'model': response.model,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store the final response message for the state machine (only if we got one from tools)
            if final_response and final_response.strip():
                updated_context['message'] = final_response
                print(f"🔧 SYSTEM: Using tool-generated response")
            else:
                # If no tool provided a response, acknowledge user input and ask for clarification
                updated_context['message'] = self._generate_acknowledgment_response(user_input, context)
                print(f"🔧 SYSTEM: No tool response - using acknowledgment fallback")
            
            # Debug output for final decision
            if next_state:
                print(f"🔧 SYSTEM: State transition requested: '{self.name}' → '{next_state}'")
            else:
                print(f"🔧 SYSTEM: Staying in current state '{self.name}' (action: {next_action.name})")
            
            return next_action, next_state, updated_context
            
        except Exception as e:
            # Fallback to error handling with acknowledgment
            print(f"🔧 SYSTEM: ERROR in LLM processing: {str(e)} - using fallback")
            updated_context = context.copy()
            updated_context['llm_error'] = str(e)
            updated_context['message'] = self._generate_acknowledgment_response(user_input, context, has_error=True)
            print(f"🔧 SYSTEM: Staying in state '{self.name}' due to error")
            return StateResult.CONTINUE, None, updated_context
    
    def _handle_tool_call(self, tool_call, context: Dict[str, Any], user_input: str) -> Optional[Dict[str, Any]]:
        """Handle individual tool calls"""
        tool_name = tool_call.name
        args = tool_call.arguments
        
        print(f"🔧 SYSTEM: Processing tool '{tool_name}' with args: {args}")
        
        try:
            if tool_name == "extract_patient_info":
                return self._handle_patient_info_extraction(args, context)
            elif tool_name == "analyze_appointment_request":
                return self._handle_appointment_analysis(args, context)
            elif tool_name == "parse_datetime_request":
                return self._handle_datetime_parsing(args, context)
            elif tool_name == "generate_response":
                return self._handle_response_generation(args, context)
            else:
                print(f"🔧 SYSTEM: Unknown tool '{tool_name}' - ignoring")
                return None
        except Exception as e:
            print(f"🔧 SYSTEM: Error processing tool '{tool_name}': {str(e)}")
            return None
    
    def _handle_patient_info_extraction(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient information extraction"""
        updates = {}
        
        if args.get('name') and args.get('confidence', 0) > 0.7:
            updates['extracted_name'] = args['name']
            updates['patient_name'] = args['name']  # Store in expected key
        if args.get('email') and args.get('confidence', 0) > 0.7:
            updates['extracted_email'] = args['email']
            updates['patient_contact'] = args['email']  # Store in expected key
        if args.get('phone') and args.get('confidence', 0) > 0.7:
            updates['extracted_phone'] = args['phone']
            updates['patient_contact'] = args['phone']  # Store in expected key
        
        return {'context_updates': updates}
    
    def _handle_appointment_analysis(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment request analysis"""
        updates = {}
        
        if args.get('intent') and args.get('confidence', 0) > 0.7:
            updates['detected_intent'] = args['intent']
        if args.get('appointment_type'):
            updates['suggested_appointment_type'] = args['appointment_type']
        if args.get('specialty'):
            updates['suggested_specialty'] = args['specialty']
        if args.get('doctor_name'):
            updates['suggested_doctor'] = args['doctor_name']
        if args.get('urgency'):
            updates['urgency_level'] = args['urgency']
        
        return {'context_updates': updates}
    
    def _handle_datetime_parsing(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle datetime parsing"""
        updates = {}
        
        if args.get('date') and args.get('confidence', 0) > 0.7:
            updates['parsed_date'] = args['date']
        if args.get('time') and args.get('confidence', 0) > 0.7:
            updates['parsed_time'] = args['time']
        if args.get('time_of_day'):
            updates['preferred_time_of_day'] = args['time_of_day']
        if args.get('relative_reference'):
            updates['relative_time_ref'] = args['relative_reference']
        if args.get('flexibility'):
            updates['time_flexibility'] = args['flexibility']
        
        return {'context_updates': updates}
    
    def _handle_response_generation(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle response generation"""
        result = {
            'response': args.get('response', ''),
            'next_action': args.get('next_action', 'continue'),
            'context_updates': args.get('context_updates', {})
        }
        
        if args.get('next_state'):
            result['next_state'] = args['next_state']
        
        return result
    
    def _generate_acknowledgment_response(self, user_input: str, context: Dict[str, Any], has_error: bool = False) -> str:
        """Generate a polite acknowledgment response that asks for clarification based on current state"""
        current_state = self.name
        
        # Acknowledge what the user said
        acknowledgment = f"I understand you said '{user_input.strip()}'. "
        
        if has_error:
            acknowledgment += "I'm having some technical difficulties, but I'd still like to help you. "
        
        # State-specific clarification requests
        if current_state == "GREETING":
            clarification = "To get started with scheduling your appointment, could you please tell me your name and what type of appointment you need?"
        elif current_state == "COLLECT_PATIENT_INFO":
            # Check both extracted and standard keys for robustness
            has_name = context.get('patient_name') or context.get('extracted_name')
            has_contact = context.get('patient_contact') or context.get('extracted_email') or context.get('extracted_phone')
            
            if not has_name:
                clarification = "Could you please tell me your full name so I can help you schedule an appointment?"
            elif not has_contact:
                clarification = "I have your name. Could you also provide your phone number or email address?"
            else:
                clarification = "I have your contact information. What type of appointment would you like to schedule?"
        elif current_state == "COLLECT_APPOINTMENT_TYPE":
            clarification = "What type of appointment are you looking for? For example, a general checkup, consultation, or something specific?"
        elif current_state == "COLLECT_DOCTOR_PREFERENCE":
            clarification = "Do you have a preferred doctor, or would you like me to suggest one based on your appointment type?"
        elif current_state == "COLLECT_DATE_TIME":
            clarification = "When would you prefer to schedule your appointment? You can mention a specific date, day of the week, or time preference."
        else:
            clarification = "Could you please provide more details so I can better assist you with your appointment?"
        
        return acknowledgment + clarification
