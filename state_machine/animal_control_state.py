from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from datetime import datetime
import json

from agents.llm_service import get_llm_service, get_tool_manager
from .context_fields import ContextField
from settings import AVAILABLE_MODELS, LLM_CONFIG

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
        return f"""You are AnimalControlBot, a voice assistant helping users with animal control services over the phone. 
        
Current State: {self.name}
Your role: Process spoken input and guide users through the animal control service process.

Voice Interaction Guidelines:
- Keep responses brief (under 30 words when possible) and conversational
- Use simple, clear language suitable for speaking
- Avoid complex sentences or technical jargon
- Ask only one question at a time
- Confirm important information by repeating it back
- Use natural speech patterns and contractions (I'm, we'll, etc.)
- Avoid listing multiple options - present choices one by one
- Speak as if you're having a phone conversation
- Be patient and offer to repeat information if needed

CRITICAL INSTRUCTIONS:
- ALWAYS use the generate_response tool to provide your final response and next action
- When unsure or confused about user input, DO NOT use generic fallbacks
- Instead, use generate_response to ask for clarification about specific details you need
- Never leave a user message without a proper response through the generate_response tool
- If you don't understand the user's intent, use generate_response to ask a clarifying question"""
    
    def process_state_entry(self, context: Dict[str, Any], previous_state: str) -> str:
        """
        Process entry into this state with a dedicated LLM call.
        This is the second phase of the two-call architecture for state transitions.
        
        Args:
            context: The current conversation context
            previous_state: The name of the previous state
            
        Returns:
            A response message to display to the user
        """
        
        # Create a specialized prompt for state entry
        entry_prompt = self._create_state_entry_prompt(context, previous_state)
        
        # Make LLM call with the specialized prompt
        try:
            # Build messages for the LLM
            messages = [
                {"role": "system", "content": entry_prompt},
                {"role": "user", "content": f"Generate an appropriate response for entering the {self.name} state. Context: {json.dumps(self._get_relevant_context(context))}"},
            ]
            
            # Add conversation history if available
            if context.get('conversation_history'):
                # Add last few turns of conversation history
                history = context['conversation_history'][-3:] if len(context['conversation_history']) > 3 else context['conversation_history']
                for turn in history:
                    role = "assistant" if turn['speaker'] == "SYSTEM" else "user"
                    messages.append({"role": role, "content": turn['message']})
            
            # Get available tools for this state
            tools = get_tool_manager().get_tools_for_state(self.name)
            
            # Make LLM call
            print(f"🔧 SYSTEM: Making LLM call for state entry '{self.name}' with {len(tools)} tools available")
            response = get_llm_service().chat_completion(
                messages=messages,
                tools=tools,
                model=self.model
            )
            
            # Process the response
            if response.tool_calls:
                # Handle tool calls
                for tool_call in response.tool_calls:
                    tool_result = self._handle_tool_call(tool_call, context, "")
                    if tool_result and 'response' in tool_result:
                        return tool_result['response']
            
            # If no tool calls or no valid response from tools, use the direct response
            if response.content:
                return response.content.strip()
                
        except Exception as e:
            print(f"🔧 SYSTEM: Error generating state entry response: {str(e)}")
        
        # Fallback to the standard enter method if the specialized approach fails
        return self.enter(context)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """
        Enter this state and generate an initial response.
        
        Args:
            context: Current conversation context
            
        Returns:
            The message to display to the user.
        """
        # Default implementation: return a generic message
        # Subclasses should override this for better responses
        return f"You are now in the {self.name} state." + self.generate_contextual_prompt(context)
        
    def _create_state_entry_prompt(self, context: Dict[str, Any], previous_state: str) -> str:
        """Create a specialized prompt for entering this state from another state"""
        base_prompt = self.system_prompt
        
        # Check if we have a specialized transition prompt for this transition
        if hasattr(self, 'transition_prompts') and previous_state in self.transition_prompts:
            # Use the specialized transition prompt
            transition_guidance = self.transition_prompts[previous_state]
        else:
            # Use the default transition guidance
            transition_guidance = f"""

You are now in the {self.name} state after transitioning from {previous_state}.

Your task is to generate an appropriate response acknowledging this transition and guiding the user through this new state.

When generating your response:
1. Acknowledge any information already collected in the previous state
2. Explain what will happen in this new state (if appropriate)
3. Ask for any additional information needed in this state
4. Be natural and conversational
5. Don't repeat information the user has already provided

Remember to use the generate_response tool for your final response.
"""
        
        return base_prompt + "\n\n" + transition_guidance
    
    def generate_contextual_prompt(self, context: Dict[str, Any]) -> str:
        """
        Generate a contextual prompt based on the current state and context.
        This uses the LLM to create a natural, context-aware message.
        """
        try:
            # Build a simple message for the LLM
            messages = [
                {"role": "system", "content": self.system_prompt + "\n\nYou are generating an initial prompt for the user based on the current context. Be natural and conversational."},
                {"role": "user", "content": f"Generate a contextual prompt for the {self.name} state. Current context: {json.dumps(self._get_relevant_context(context))}"},
            ]
            
            # Make LLM call without tools
            response = get_llm_service().chat_completion(
                messages=messages,
                model=self.model
            )
            
            if response and response.content:
                return response.content.strip()
            
        except Exception as e:
            print(f"🔧 SYSTEM: Error generating contextual prompt: {str(e)}")
        
        # Fallback to a simple generic prompt if LLM fails
        return f"Welcome to the {self.name} state. How can I help you?"
    
    def _get_relevant_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant context for prompt generation.
        Filters out internal state machine details.
        """
        # Keys to exclude from context sent to LLM
        exclude_keys = ['conversation_history', 'last_llm_response', 'message', 'error_message']
        
        # Create a filtered context
        filtered_context = {k: v for k, v in context.items() 
                           if k not in exclude_keys and not isinstance(v, (dict, list)) and v is not None}
        
        # Add information about missing fields if available
        if hasattr(self, 'required_fields'):
            missing_fields = self._get_missing_fields(context)
            filtered_context['missing_fields'] = missing_fields
            
        return filtered_context
    
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
        
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing with field mapping"""
        if not hasattr(self, 'required_fields'):
            return []
            
        # Define field mappings - what other fields can satisfy a required field
        field_mappings = {
            ContextField.IDENTIFYING_FEATURES.value: [
                'distinctive_features', 'has_collar', 'has_tags', 'has_microchip'
            ],
            ContextField.OWNER_CONTACT.value: [
                # If both owner_name and owner_phone exist, owner_contact is satisfied
                ('owner_name', 'owner_phone'),
                'contact_info',
                'phone_number',
                'email'
            ],
            ContextField.ANIMAL_DESCRIPTION.value: [
                'animal_color', 'breed', 'animal_size', 'animal_weight'
            ],
            ContextField.ANIMAL_CONDITION.value: [
                'condition', 'health_status', 'severity'
            ]
        }
        
        missing = []
        
        # Check each required field with mapping for related fields
        for field in self.required_fields:
            # Check if the field itself exists
            if context.get(field):
                continue
                
            # Check if any mapped fields exist that would satisfy this requirement
            if field in field_mappings:
                # Check each possible mapping
                field_satisfied = False
                for mapping in field_mappings[field]:
                    # Handle tuple case (all fields in tuple must exist)
                    if isinstance(mapping, tuple):
                        if all(context.get(m) for m in mapping):
                            field_satisfied = True
                            break
                    # Handle single field case
                    elif context.get(mapping):
                        field_satisfied = True
                        break
                        
                if field_satisfied:
                    continue
            
            # If we get here, the field is missing
            missing.append(field)
                
        return missing
    
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
    
    def _debug_context(self, context: Dict[str, Any], label: str) -> None:
        """Print debug information about the current context"""
        # Create a filtered version of context for debugging
        debug_context = {k: v for k, v in context.items() 
                        if k not in ['conversation_history', 'last_llm_response'] 
                        and not isinstance(v, (dict, list)) and v is not None}
        
        print(f"🔧 CONTEXT DEBUG [{label}] State: {self.name} - {json.dumps(debug_context, indent=2)}")
        
        # If we have required fields, show which ones are missing
        if hasattr(self, 'required_fields'):
            missing = self._get_missing_fields(context)
            if missing:
                print(f"🔧 MISSING FIELDS: {', '.join(missing)}")
            else:
                print(f"🔧 ALL REQUIRED FIELDS COLLECTED")
                
            # Show what information we're going to ask for next
            if missing:
                next_field = missing[0]
                print(f"🔧 NEXT FIELD TO COLLECT: {next_field}")
            else:
                print(f"🔧 READY TO TRANSITION TO NEXT STATE")
                
    def _enhance_system_prompt_with_context(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Enhance the system prompt with context information"""
        # Add information about what we already know
        prompt = base_prompt + "\n\n===== CURRENT CONTEXT INFORMATION =====\n"
        
        # Add progress bar if applicable
        if hasattr(self, 'required_fields'):
            progress_bar = self.generate_progress_bar(context)
            if progress_bar:
                prompt += f"\n{progress_bar}\n"
        
        # Add known information
        known_info = []
        for key, value in context.items():
            if key not in ['conversation_history', 'last_llm_response', 'message', 'error_message'] \
               and not isinstance(value, (dict, list)) and value is not None:
                known_info.append(f"- {key}: {value}")
        
        if known_info:
            prompt += "\nKnown Information:\n" + "\n".join(known_info) + "\n"
        
        # Add information about missing fields if this state has required fields
        if hasattr(self, 'required_fields'):
            missing_fields = self._get_missing_fields(context)
            if missing_fields:
                prompt += "\nMissing Information (collect in this order):\n" + "\n".join([f"- {field}" for field in missing_fields]) + "\n"
            else:
                prompt += "\nAll required information has been collected.\n"
                
        prompt += "\n===== END CONTEXT INFORMATION =====\n"
        return prompt
        
    def generate_progress_bar(self, context: Dict[str, Any]) -> str:
        """Generate a progress bar showing completion status"""
        if not hasattr(self, 'required_fields') or not self.required_fields:
            return ""
            
        # Calculate progress
        total_fields = len(self.required_fields)
        missing_fields = self._get_missing_fields(context)
        completed_fields = total_fields - len(missing_fields)
        progress_percent = int((completed_fields / total_fields) * 100)
        
        # Create progress bar
        return f"[Progress: {progress_percent}% - Step {completed_fields + 1 if completed_fields < total_fields else total_fields} of {total_fields}]"
        
    def generate_acknowledgment(self, context: Dict[str, Any]) -> str:
        """Generate an acknowledgment of information already provided"""
        acknowledgment = ""
        
        # Add animal type and name if available
        if context.get('animal_type'):
            pet_type = context.get('animal_type')
            pet_name = context.get('animal_name', '')
            
            if pet_name:
                acknowledgment += f"I understand you're looking for your {pet_type} named {pet_name}. "
            else:
                acknowledgment += f"I understand you're looking for your {pet_type}. "
                
        # Add other acknowledgments based on context
        
        return acknowledgment
    
    def process_input_with_llm(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """Process input using LLM with appropriate tools"""
        try:
            # Debug context information before LLM call
            self._debug_context(context, "Before LLM call")
            
            # Build message history
            messages = self._build_messages(user_input, context)
            
            # Add enhanced context information to system prompt
            messages[0]["content"] = self._enhance_system_prompt_with_context(messages[0]["content"], context)
            
            # Get tools for current state
            tools = get_tool_manager().get_tools_for_state(self.name)
            
            # Make LLM call
            print(f"🔧 SYSTEM: Making LLM call for state '{self.name}' with {len(tools)} tools available")
            response = get_llm_service().chat_completion(
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
            
            # For transitions, we don't need a response message
            # The next state's enter method will generate the response
            if next_action == StateResult.TRANSITION and next_state:
                # Check if a response was provided (it's now optional)
                if final_response and final_response.strip():
                    # Log that a response was provided but won't be used
                    print(f"🔧 SYSTEM: Transition requested with message: '{final_response[:50]}...' (will be ignored)")
                    # We don't store the message anywhere as it won't be used
                else:
                    # This is the expected behavior with the updated tool definition
                    print(f"🔧 SYSTEM: Transition requested without message (correct behavior)")
                
                # Clear any existing message to ensure it doesn't interfere with the next state
                if 'message' in updated_context:
                    del updated_context['message']
            # For other actions, store the final response message (only if we got one from tools)
            elif final_response and final_response.strip():
                updated_context['message'] = final_response
                # Print both the system message and what will be shown to the user
                print(f"🔧 SYSTEM: Using tool-generated response")
                print(f"🤖 {final_response}")
            else:
                # If no tool provided a response, use the LLM's direct response if available
                if response.content and response.content.strip():
                    updated_context['message'] = response.content.strip()
                    print(f"🔧 SYSTEM: No tool response - using LLM direct response")
                    print(f"🤖 {response.content.strip()}")
                else:
                    # If no response at all, try to call generate_response again with a clarification request
                    try:
                        # Create a clarification request based on the current state and context
                        clarification_message = f"I need more information to help you with your {context.get('animal_type', 'animal')} concern. Could you please provide more details?"
                        
                        # Call the generate_response tool directly
                        response_tool = tool_manager.get_tool("generate_response")
                        if response_tool:
                            tool_result = response_tool.execute({
                                'response': clarification_message,
                                'next_action': 'continue'
                            })
                            if tool_result and 'response' in tool_result:
                                updated_context['message'] = tool_result['response']
                                print(f"🔧 SYSTEM: Using generate_response tool for clarification")
                            else:
                                # Fallback if tool execution fails
                                updated_context['message'] = clarification_message
                                print(f"🔧 SYSTEM: Using clarification message as fallback")
                        else:
                            # Fallback if tool not found
                            updated_context['message'] = clarification_message
                            print(f"🔧 SYSTEM: Using clarification message as fallback (tool not found)")
                    except Exception as tool_error:
                        # Ultimate fallback if everything else fails
                        print(f"🔧 SYSTEM: Error in fallback handling: {str(tool_error)}")
                        updated_context['message'] = f"I need more information about your request. Could you please provide more details?"
                        print(f"🔧 SYSTEM: Using simple clarification as ultimate fallback")
            
            # Debug output for final decision
            if next_state:
                print(f"🔧 SYSTEM: '{self.name}' → '{next_state}'")
            else:
                print(f"🔧 SYSTEM: Staying in current state '{self.name}' (action: {next_action.name})")
            
            return next_action, next_state, updated_context
            
        except Exception as e:
            # Fallback to error handling
            print(f"🔧 SYSTEM: ERROR in LLM processing: {str(e)} - using fallback")
            updated_context = context.copy()
            updated_context['llm_error'] = str(e)
            
            try:
                # Try to use the generate_response tool directly for error handling
                error_message = f"I need a bit more information to help you properly. Could you please provide more details about your {context.get('animal_type', 'animal')} concern?"
                
                # Call the generate_response tool directly
                response_tool = tool_manager.get_tool("generate_response")
                if response_tool:
                    tool_result = response_tool.execute({
                        'response': error_message,
                        'next_action': 'continue'
                    })
                    if tool_result and 'response' in tool_result:
                        updated_context['message'] = tool_result['response']
                        print(f"🔧 SYSTEM: Using generate_response tool for error recovery")
                    else:
                        updated_context['message'] = error_message
                        print(f"🔧 SYSTEM: Using error message as fallback")
                else:
                    updated_context['message'] = error_message
                    print(f"🔧 SYSTEM: Using error message as fallback (tool not found)")
            except Exception as tool_error:
                # Ultimate fallback if everything else fails
                print(f"🔧 SYSTEM: Error in fallback handling: {str(tool_error)}")
                updated_context['message'] = f"I need more information to help you properly. Could you please provide more details?"
                print(f"🔧 SYSTEM: Using simple clarification as ultimate fallback")
                
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
            elif tool_name == "update_context":
                return self._handle_update_context(args, context)
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
            
    def _handle_update_context(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context updates from the LLM"""
        updates = {}
        
        if args.get('context_updates'):
            # Get the raw updates from the LLM
            raw_updates = args['context_updates']
            
            # Normalize all field names using the ContextField enum
            normalized_updates = {}
            for key, value in raw_updates.items():
                # Convert the key to its canonical form
                canonical_key = ContextField.normalize_field(key)
                normalized_updates[canonical_key] = value
            
            # Apply any special handling or derived values
            self._apply_derived_values(normalized_updates)
            
            updates = normalized_updates
            print(f"🔧 SYSTEM: LLM updated context with {len(updates)} key(s): {list(updates.keys())}")
        
        return {'context_updates': updates}
        
    def _apply_derived_values(self, updates: Dict[str, Any]) -> None:
        """Apply any special handling or derived values to context updates"""
        # Example: If we have condition='coughing up blood', set animal_condition='critical'
        if updates.get(ContextField.CONDITION.value) == 'coughing up blood':
            updates[ContextField.ANIMAL_CONDITION.value] = 'critical'
            
        # Example: If we have severity='high', set animal_condition='critical'
        if updates.get(ContextField.SEVERITY.value) == 'high':
            updates[ContextField.ANIMAL_CONDITION.value] = 'critical'
            
        # Example: If we have emergency_status='critical', set animal_condition='critical'
        if updates.get(ContextField.EMERGENCY_STATUS.value) == 'critical':
            updates[ContextField.ANIMAL_CONDITION.value] = 'critical'
    
    def _handle_animal_request_analysis(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle animal control request analysis"""
        updates = {}
        
        # Map arguments to context fields using the enum
        field_mapping = {
            'intent': ContextField.DETECTED_INTENT.value,
            'animal_type': ContextField.ANIMAL_TYPE.value,
            'service_type': ContextField.SERVICE_TYPE.value,
            'location': ContextField.LOCATION.value,
            'urgency': ContextField.URGENCY_LEVEL.value
        }
        
        # Only add fields that exist in the args and have sufficient confidence
        for arg_name, context_field in field_mapping.items():
            if arg_name == 'intent':
                # Special case for intent which requires confidence check
                if args.get(arg_name) and args.get('confidence', 0) > 0.7:
                    updates[context_field] = args[arg_name]
            elif args.get(arg_name):
                updates[context_field] = args[arg_name]
        
        # Apply any special handling or derived values
        if updates.get(ContextField.URGENCY_LEVEL.value) == 'emergency':
            updates[ContextField.ANIMAL_CONDITION.value] = 'critical'
        
        return {'context_updates': updates}
    
    def _handle_datetime_parsing(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle datetime parsing"""
        updates = {}
        
        # Map arguments to context fields using the enum
        field_mapping = {
            'date': 'parsed_date',  # Not in enum yet
            'time': 'parsed_time',  # Not in enum yet
            'time_of_day': 'preferred_time_of_day',  # Not in enum yet
            'relative_reference': 'relative_time_ref',  # Not in enum yet
            'flexibility': 'time_flexibility'  # Not in enum yet
        }
        
        # Only add fields that exist in the args and have sufficient confidence
        for arg_name, context_field in field_mapping.items():
            if arg_name in ['date', 'time']:
                # Special case for date/time which requires confidence check
                if args.get(arg_name) and args.get('confidence', 0) > 0.7:
                    updates[context_field] = args[arg_name]
            elif args.get(arg_name):
                updates[context_field] = args[arg_name]
        
        # If we have both date and time, try to create a datetime object
        appointment_datetime = None
        if 'parsed_date' in updates and 'parsed_time' in updates:
            try:
                date_str = updates['parsed_date']
                time_str = updates['parsed_time']
                datetime_str = f"{date_str} {time_str}"
                parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                # Store as ISO format string instead of datetime object for JSON serialization
                updates[ContextField.SELECTED_DATE.value] = parsed_datetime.isoformat()
                appointment_datetime = parsed_datetime
            except ValueError:
                pass
        
        # Generate a response message based on the parsed date/time
        response_message = ""
        if appointment_datetime:
            # Format the date nicely for the response
            formatted_date = appointment_datetime.strftime("%A, %B %d at %I:%M %p")
            response_message = f"I've scheduled your appointment for {formatted_date}. Does this time work for you?"
        elif 'parsed_date' in updates:
            # We have a date but no valid time
            response_message = f"I've noted the date {updates['parsed_date']}. What time would work best for you?"
        elif 'parsed_time' in updates:
            # We have a time but no valid date
            response_message = f"I've noted the time {updates['parsed_time']}. What date would you prefer?"
        else:
            # We couldn't parse a valid date or time
            response_message = "I couldn't quite understand that date/time. Could you please provide a specific date and time for your appointment?"
        
        return {
            'context_updates': updates,
            'response': response_message,
            'next_action': 'continue'
        }
    
    def _handle_response_generation(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle response generation"""
        # Get the basic response information
        response = args.get('response', '')
        next_action = args.get('next_action', 'continue')
        
        # Get any context updates and normalize them
        raw_updates = args.get('context_updates', {})
        normalized_updates = {}
        
        # Normalize all field names using the ContextField enum
        for key, value in raw_updates.items():
            # Convert the key to its canonical form
            canonical_key = ContextField.normalize_field(key)
            normalized_updates[canonical_key] = value
        
        # Apply any special handling or derived values
        self._apply_derived_values(normalized_updates)
        
        # Build the result
        result = {
            'response': response,
            'next_action': next_action,
            'context_updates': normalized_updates
        }
        
        # Add next_state if provided
        if args.get('next_state'):
            result['next_state'] = args['next_state']

        return result
    