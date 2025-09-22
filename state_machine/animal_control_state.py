from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from datetime import datetime
import json

from agents.llm_service import llm_service, tool_manager
from config.settings import AVAILABLE_MODELS

class StateResult(Enum):
    """Possible results from state execution"""
    CONTINUE = "continue"  # Stay in current state
    TRANSITION = "transition"  # Move to next state
    ERROR = "error"  # Error occurred
    COMPLETE = "complete"  # Conversation complete

class AnimalControlState(ABC):
    """Consolidated state class for animal control with LLM capabilities"""
    
    def __init__(self, name: str, system_prompt: str = None, database = None):
        self.name = name
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.conversation_history = []
        self.model = AVAILABLE_MODELS.get('conversation')
        self.retry_count = 0
        self.max_retries = 3
        self.database = database
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for this state"""
        return f"""You are AnimalControlBot, an AI assistant helping users with animal control services. 
        
Current State: {self.name}
Your role: Process user input and guide them through the animal control service process.

Guidelines:
- Be helpful, professional, and empathetic
- Ask for information step by step
- Validate user inputs appropriately
- Use the provided tools to extract information and generate responses
- Keep responses concise but informative
- Handle errors gracefully and offer alternatives

Always use the generate_response tool to provide your final response and next action."""
    
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
        
        # Animal information
        if context.get('animal_type'):
            info_parts.append(f"Animal type: {context['animal_type']}")
        if context.get('animal_name'):
            info_parts.append(f"Animal name: {context['animal_name']}")
        if context.get('animal_description'):
            info_parts.append(f"Description: {context['animal_description']}")
        
        # Location information
        if context.get('location'):
            info_parts.append(f"Location: {context['location']}")
        if context.get('last_seen_location'):
            info_parts.append(f"Last seen: {context['last_seen_location']}")
        if context.get('location_found'):
            info_parts.append(f"Found at: {context['location_found']}")
        
        # Contact information
        if context.get('owner_name'):
            info_parts.append(f"Owner: {context['owner_name']}")
        if context.get('owner_contact'):
            info_parts.append(f"Contact: {context['owner_contact']}")
        
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
            print(f"Model used: {response.model}")
            print(f"Tokens used: {response.usage.get('total_tokens')}")
            print(f"Response time: {response.usage.get('total_tokens')}")
            
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
            if tool_name == "analyze_request":
                return self._handle_animal_request_analysis(args, context)
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
    
    def _handle_animal_request_analysis(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle animal control request analysis"""
        updates = {}
        
        if args.get('intent') and args.get('confidence', 0) > 0.7:
            updates['detected_intent'] = args['intent']
        if args.get('animal_type'):
            updates['animal_type'] = args['animal_type']
        if args.get('service_type'):
            updates['service_type'] = args['service_type']
        if args.get('location'):
            updates['location'] = args['location']
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
        
        # State-specific clarification requests for animal control
        if current_state == "GREETING":
            clarification = "How can I assist you with animal control services today? I can help with reporting lost or found animals, emergency cases, pet surrenders, or providing general information."
        elif current_state == "EMERGENCY_CASE":
            clarification = "For emergency animal situations, could you please provide details about the animal and its location?"
        elif current_state == "REPORT_FOUND":
            clarification = "To report a found animal, could you please describe the animal and where you found it?"
        elif current_state == "REPORT_LOST":
            clarification = "I'm sorry to hear about your lost pet. Could you please describe your pet and where it was last seen?"
        elif current_state == "PET_SURRENDER":
            clarification = "For pet surrenders, could you tell me about the animal you're considering surrendering?"
        elif current_state == "SCHEDULE_SURRENDER":
            clarification = "When would be a convenient time for you to schedule the surrender?"
        elif current_state == "GENERAL_INFO":
            clarification = "What specific information about animal control services are you looking for?"
        else:
            clarification = "Could you please provide more details so I can better assist you with your animal control needs?"
        
        return acknowledgment + clarification
